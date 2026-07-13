# -*- coding: utf-8 -*-

import json
import requests

import prompts
from config.settings import settings
from utils import logger
from utils.redis_tool import RedisClient

TTL = 40
MAX_HISTORY = 6
REDIS_KEY = "voice:rewrite_history:{}"
_redis_client = RedisClient()


def request_rewrite(query, last_answer, sender_id):
    history = _load_history(sender_id)
    if history and last_answer:
        history[-1]["content"] = last_answer

    result = _llm_rewrite(query, history) if settings.api_key and settings.base_url else _rule_rewrite(query, history)
    if not result or result == "否":
        result = query

    if len(set(result).intersection(query)) < max(1, len(query) / 4):
        result = query

    logger.info("Query rewrite: %s -> %s", query, result)
    history.append({"role": "user", "content": result})
    history.append({"role": "assistant", "content": ""})
    _redis_client.set(REDIS_KEY.format(sender_id), json.dumps(history[-MAX_HISTORY:], ensure_ascii=False), ex=TTL)
    return result


def _load_history(sender_id):
    raw = _redis_client.get(REDIS_KEY.format(sender_id))
    if not raw:
        return []
    try:
        return json.loads(raw)[-MAX_HISTORY:]
    except json.JSONDecodeError:
        return []


def _llm_rewrite(query, history):
    if not history:
        return query
    prompt = "# 对话历史\n{}\nA:{}".format(_format_history(history), query)
    headers = {"Authorization": settings.api_key, "Content-Type": "application/json"}
    data = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": prompts.REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "top_p": 1,
    }
    try:
        response = requests.post(settings.base_url, headers=headers, data=json.dumps(data), timeout=settings.request_timeout)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.error("Rewrite API failed: %s", exc)
        return _rule_rewrite(query, history)


def _rule_rewrite(query, history):
    if not history:
        return query
    recent_text = "\n".join(item.get("content", "") for item in history[-4:])
    artist = _find_first(recent_text, ["周杰伦", "林俊杰", "邓紫棋", "陈奕迅"])
    city = _find_first(recent_text, ["北京", "上海", "广州", "深圳", "杭州"])
    if artist and ("他的歌" in query or "她的歌" in query):
        return query.replace("他的歌", f"{artist}的歌").replace("她的歌", f"{artist}的歌")
    if city and query in {"明天呢", "那明天呢"}:
        return f"{city}明天天气怎么样"
    if city and query.startswith("那") and query.endswith("呢"):
        return f"{query[1:-1]}天气怎么样"
    return query


def _format_history(history):
    lines = []
    for item in history[-MAX_HISTORY:]:
        role = "A" if item.get("role") == "user" else "B"
        lines.append(f"{role}:{item.get('content', '')}")
    return "\n".join(lines)


def _find_first(text, candidates):
    return next((item for item in candidates if item in text), "")
