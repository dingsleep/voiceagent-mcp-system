# -*- coding: utf-8 -*-

import requests

import prompts
from config.settings import settings
from utils import logger

NLG_PROMPT = prompts.NLG_PROMPT


def request_nlg(query, tool_response):
    if not settings.api_key or not settings.base_url:
        return _fallback_nlg(query, tool_response)

    headers = {"Content-Type": "application/json", "Authorization": settings.api_key}
    body = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": NLG_PROMPT.format(query, tool_response)}],
    }
    try:
        response = requests.post(settings.base_url, headers=headers, json=body, timeout=settings.request_timeout)
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"]
        logger.info("NLG result: %s", answer)
        return answer
    except Exception as exc:
        logger.error("Call NLG API failed: %s", exc)
        return _fallback_nlg(query, tool_response)


def _fallback_nlg(query, tool_response):
    if not tool_response:
        return prompts.DEFAULT_NLG
    return str(tool_response)[:80]


if __name__ == "__main__":
    print(request_nlg("今天天气怎么样", "城市：北京\n天气：晴\n温度：18-27C"))
