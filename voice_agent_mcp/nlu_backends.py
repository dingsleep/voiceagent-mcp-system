"""NLU backend adapters for the runnable vehicle Agent demo."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Callable, Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

from .nlu import NLUResult, parse_task


REMOTE_FUNCTION_MAP = {
    "Query_Weather": "weather.query",
    "Query_Timely_Weather": "weather.query",
    "Search_Music": "music.play",
    "Play_Online_Music": "music.play",
    "Go_POI": "map.route",
    "Go_Company": "map.route",
}

REMOTE_INTENT_MAP = {
    "Query_Weather": "weather_query",
    "Query_Timely_Weather": "weather_query",
    "Search_Music": "music_play",
    "Play_Online_Music": "music_play",
    "Go_POI": "map_route",
    "Go_Company": "map_route",
}


@dataclass(frozen=True)
class NLUDecision:
    result: NLUResult
    backend: str
    latency_ms: int
    fallback_reason: str = ""


class NLUBackend(Protocol):
    name: str

    def parse(self, query: str, trace_id: str) -> NLUDecision: ...

    def describe(self) -> dict: ...


class RuleNluBackend:
    name = "rule"

    def parse(self, query: str, trace_id: str) -> NLUDecision:
        started = time.perf_counter()
        return NLUDecision(
            result=parse_task(query),
            backend=self.name,
            latency_ms=_elapsed_ms(started),
        )

    def describe(self) -> dict:
        return {"name": self.name, "mode": "local", "ready": True}


Transport = Callable[[str, dict, float], dict]


class RemoteNluBackend:
    """Adapter for the existing ``/chatnlu-server/v1`` service."""

    name = "remote"

    def __init__(self, endpoint: str, timeout_seconds: float = 3.0, transport: Transport | None = None):
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self._transport = transport or _post_json

    def parse(self, query: str, trace_id: str) -> NLUDecision:
        started = time.perf_counter()
        payload = {"query": query, "trace_id": trace_id, "enable_dm": False}
        response = self._transport(self.endpoint, payload, self.timeout_seconds)
        if response.get("source") == "fallback":
            fallback = RuleNluBackend().parse(query, trace_id)
            return NLUDecision(
                result=fallback.result,
                backend=fallback.backend,
                latency_ms=_elapsed_ms(started),
                fallback_reason=f"remote_fallback:{response.get('fallback_reason') or 'unknown'}",
            )
        result = _parse_response(response)
        return NLUDecision(result=result, backend=self.name, latency_ms=_elapsed_ms(started))

    def describe(self) -> dict:
        return {
            "name": self.name,
            "mode": "remote",
            "endpoint": self.endpoint,
            "timeout_seconds": self.timeout_seconds,
        }


def build_nlu_backend(
    mode: str | None = None,
    endpoint: str | None = None,
    timeout_seconds: float | None = None,
) -> NLUBackend:
    selected = (mode or os.getenv("VOICE_AGENT_NLU_BACKEND", "rule")).strip().lower()
    if selected == "rule":
        return RuleNluBackend()
    if selected == "remote":
        configured_endpoint = endpoint or os.getenv("VOICE_AGENT_NLU_URL") or os.getenv("NLU_URL")
        if not configured_endpoint:
            raise ValueError("remote NLU backend requires VOICE_AGENT_NLU_URL or NLU_URL")
        configured_timeout = timeout_seconds or float(os.getenv("VOICE_AGENT_NLU_TIMEOUT", "3"))
        return RemoteNluBackend(configured_endpoint, configured_timeout)
    raise ValueError(f"unsupported NLU backend: {selected}")


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
        raise RuntimeError(f"remote NLU request failed: {exc}") from exc


def _parse_response(payload: dict) -> NLUResult:
    if not isinstance(payload, dict):
        raise ValueError("remote NLU response must be an object")
    intent = payload.get("intent")
    function = payload.get("function")
    slots = payload.get("slots", {})
    if not isinstance(intent, str) or not isinstance(function, str) or not isinstance(slots, dict):
        raise ValueError("remote NLU response must contain string intent/function and object slots")
    return NLUResult(
        intent=REMOTE_INTENT_MAP.get(function, intent),
        function=REMOTE_FUNCTION_MAP.get(function, function),
        slots=_normalize_slots(function, slots),
    )


def _normalize_slots(function: str, slots: dict) -> dict:
    if function in {"Query_Weather", "Query_Timely_Weather"}:
        normalized = {}
        if city := _first_slot(slots, "City", "city"):
            normalized["city"] = city
        if date := _first_slot(slots, "Date", "date", "Time", "time"):
            normalized["date"] = date
        return normalized
    if function in {"Search_Music", "Play_Online_Music"}:
        artist = _first_slot(slots, "Singer", "singer", "Artist", "artist", "\u6b4c\u624b")
        return {"artist": artist} if artist else {}
    if function == "Go_POI":
        destination = _first_slot(slots, "POI", "poi", "Destination", "destination", "Name", "name")
        return {"destination": destination} if destination else {}
    if function == "Go_Company":
        return {"destination": _first_slot(slots, "POI", "Destination") or "\u516c\u53f8"}
    return slots


def _first_slot(slots: dict, *names: str):
    for name in names:
        value = slots.get(name)
        if value not in (None, ""):
            return value
    return ""


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
