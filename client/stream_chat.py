# -*- coding: utf-8 -*-

import json
import re
import requests

import prompts
from config.settings import settings
from utils import logger
from utils.redis_tool import RedisClient

MAX_HIS = 6
TTL = 45
REDIS_KEY = "voice:chat_history:{}"
_redis_client = RedisClient()
SYSTEM_PROMPT = prompts.BOT_CHAT_SYSTEM_PROMPT


def request_chat(query, sender_id, multiturn=True):
    if not settings.api_key or not settings.bot_url:
        return {"mock": True, "answer": _mock_answer(query)}

    history = _load_history(sender_id) if multiturn else []
    headers = {"Authorization": settings.api_key, "Content-Type": "application/json"}
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *history, {"role": "user", "content": query}]
    data = {"model": settings.llm_model, "messages": messages, "stream": True}
    try:
        return requests.post(
            settings.bot_url,
            headers=headers,
            data=json.dumps(data),
            stream=True,
            timeout=settings.request_timeout,
        )
    except Exception as exc:
        logger.error("Bot chat error: %s", exc)
        return {"mock": True, "answer": "抱歉，聊天服务暂时不可用，请稍后再试。"}


def process_chat(response, query, sender_id):
    if isinstance(response, dict) and response.get("mock"):
        answer = response["answer"]
        yield from _split(answer)
        _save_history(sender_id, query, answer)
        return

    if response is None or response == "N":
        yield "抱歉，网络有点问题，请稍后再试。"
        return

    answer = ""
    buffer = ""
    for line in response.iter_lines(chunk_size=1, decode_unicode=False, delimiter=b"\n"):
        line = line.decode("utf-8").strip()
        if not line:
            continue
        data = line.removeprefix("data: ")
        if data == "[DONE]":
            break
        try:
            payload = json.loads(data)
            text = payload["choices"][0].get("delta", {}).get("content", "")
        except Exception:
            continue
        if not text:
            continue
        answer += text
        buffer += text
        if re.search(r"[，。！？；,.!?]", text) or len(buffer) >= 12:
            yield buffer
            buffer = ""
    if buffer.strip():
        yield buffer
    _save_history(sender_id, query, answer)


def _load_history(sender_id):
    raw = _redis_client.get(REDIS_KEY.format(sender_id))
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _save_history(sender_id, query, answer):
    history = _load_history(sender_id)
    history.append({"role": "user", "content": query})
    history.append({"role": "assistant", "content": answer})
    _redis_client.set(REDIS_KEY.format(sender_id), json.dumps(history[-MAX_HIS:], ensure_ascii=False), ex=TTL)


def _split(text):
    buffer = ""
    for char in text:
        buffer += char
        if char in "，。！？；,.!?" or len(buffer) >= 12:
            yield buffer
            buffer = ""
    if buffer:
        yield buffer


def _mock_answer(query):
    if "笑话" in query:
        return "可以。为什么程序员喜欢安静？因为一有噪声，就想 debug。"
    return "我是车载语音助手，可以处理天气、音乐、导航等任务，也可以简单闲聊。"
