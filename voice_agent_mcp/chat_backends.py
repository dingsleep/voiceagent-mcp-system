"""OpenAI-compatible chat backend with stream timing telemetry."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Protocol

import requests

from function_call.api_auth import bearer_authorization
from config.settings import settings


@dataclass(frozen=True)
class ChatDecision:
    text: str
    trace: dict


class ChatBackend(Protocol):
    def reply(self, query: str) -> ChatDecision: ...


class RuleChatBackend:
    def reply(self, query: str) -> ChatDecision:
        return ChatDecision("我是车载多轮任务 Agent，可以处理天气、音乐与导航任务。", {"backend": "rule"})


StreamTransport = Callable[[dict], Iterable[dict]]


class DeepSeekChatBackend:
    def __init__(self, transport: StreamTransport | None = None):
        self._transport = transport or _stream_request

    def reply(self, query: str) -> ChatDecision:
        started = time.perf_counter()
        first_token_ms: int | None = None
        content: list[str] = []
        usage: dict = {}
        for chunk in self._transport(_payload(query)):
            if not first_token_ms and chunk.get("content"):
                first_token_ms = _elapsed_ms(started)
            if value := chunk.get("content"):
                content.append(value)
            if isinstance(chunk.get("usage"), dict):
                usage = _usage_summary(chunk["usage"])
        latency_ms = _elapsed_ms(started)
        completion_tokens = usage.get("completion_tokens", 0)
        trace = {
            "backend": "deepseek",
            "model": settings.llm_model,
            "first_token_ms": first_token_ms or latency_ms,
            "latency_ms": latency_ms,
            "usage": usage,
            "tokens_per_second": round(completion_tokens / (latency_ms / 1000), 1) if latency_ms and completion_tokens else 0,
        }
        return ChatDecision("".join(content) or "当前没有生成可展示的回复。", trace)


def _payload(query: str) -> dict:
    return {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "You are a concise in-vehicle assistant. Reply in Chinese."},
            {"role": "user", "content": query},
        ],
        "temperature": 0.4,
        "stream": True,
        "stream_options": {"include_usage": True},
    }


def _stream_request(payload: dict) -> Iterable[dict]:
    if not settings.api_key or not settings.bot_url:
        raise RuntimeError("chat model is not configured")
    response = requests.post(
        settings.bot_url,
        headers={"Authorization": bearer_authorization(settings.api_key), "Content-Type": "application/json"},
        json=payload,
        stream=True,
        timeout=settings.request_timeout,
    )
    response.raise_for_status()
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data:"):
            continue
        value = raw_line.removeprefix("data:").strip()
        if value == "[DONE]":
            break
        chunk = json.loads(value)
        choice = (chunk.get("choices") or [{}])[0]
        yield {"content": choice.get("delta", {}).get("content", ""), "usage": chunk.get("usage")}


def _usage_summary(usage: dict) -> dict:
    return {key: usage[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens") if isinstance(usage.get(key), int)}


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
