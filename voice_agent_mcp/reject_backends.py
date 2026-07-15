"""Reject-model adapters used by the local Agent console."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class RejectDecision:
    allowed: bool
    confidence: float | None
    latency_ms: int
    backend: str
    fallback_reason: str = ""


class RejectBackend(Protocol):
    def evaluate(self, query: str, trace_id: str) -> RejectDecision: ...


class RuleRejectBackend:
    def evaluate(self, query: str, trace_id: str) -> RejectDecision:
        return RejectDecision(True, None, 0, "rule")


Transport = Callable[[str, dict, float], dict]


class RemoteRejectBackend:
    def __init__(self, endpoint: str, threshold: float = 0.6162, timeout_seconds: float = 3.0, transport: Transport | None = None):
        self.endpoint = endpoint
        self.threshold = threshold
        self.timeout_seconds = timeout_seconds
        self._transport = transport or _post_json

    def evaluate(self, query: str, trace_id: str) -> RejectDecision:
        started = time.perf_counter()
        response = self._transport(
            self.endpoint,
            {"query": query, "trace_id": trace_id, "thres": self.threshold},
            self.timeout_seconds,
        )
        try:
            allowed = int(response["data"]) == 1
            confidence = float(response.get("score"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid reject response") from exc
        return RejectDecision(allowed, confidence, _elapsed_ms(started), "bert_tiny")


def _post_json(endpoint: str, payload: dict, timeout_seconds: float) -> dict:
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"reject request failed: {type(exc).__name__}") from exc


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
