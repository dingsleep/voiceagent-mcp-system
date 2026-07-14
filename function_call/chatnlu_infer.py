# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import prompts
from config.settings import settings
from utils import logger

try:
    from fastapi import FastAPI, Request
    import uvicorn
except ImportError:  # pragma: no cover - service mode requires runtime deps.
    FastAPI = None
    Request = object
    uvicorn = None

try:
    from function_call.function import tools1
    from function_call.slot_process import intent_slot
    from function_call.dm.factory import DMFactory
except ImportError:  # pragma: no cover - keeps direct script execution working.
    from function import tools1
    from slot_process import intent_slot
    from dm.factory import DMFactory


app = FastAPI() if FastAPI else None

MAX_CONF = 0.98
UNKNOWN_INTENT = "未知"
EMPTY_SLOT = "无"
ROOT = Path(__file__).resolve().parents[1]


def load_intent_maps():
    id2func: dict[str, str] = {}
    func2name: dict[str, str] = {}
    name2id: dict[str, str] = {}
    with (ROOT / "config" / "class.txt").open(encoding="utf-8") as mapfile:
        for line in mapfile:
            intent_id, name, func = line.strip().split(":")
            id2func[intent_id] = func
            func2name[func] = name
            name2id[name] = intent_id
    return id2func, func2name, name2id


def load_slot_map():
    with (ROOT / "config" / "slot_intent.json").open(encoding="utf-8") as slotfile:
        return json.load(slotfile)


def build_tool_map():
    tool_map: dict[str, list[dict]] = {}
    for item in tools1:
        tool_map.setdefault(item["function"]["name"], []).append(item)
    return tool_map


id2func, func2name, name2id = load_intent_maps()
slot_map = load_slot_map()
tool_map = build_tool_map()


def send_messages(messages, tool_lst):
    if not settings.api_key or not settings.base_url:
        return None

    headers = {"Authorization": settings.api_key, "Content-Type": "application/json"}
    data = {
        "model": settings.llm_model,
        "messages": messages,
        "tools": tool_lst,
        "temperature": 1e-6,
        "top_p": 0,
    }
    try:
        response = requests.post(
            settings.base_url,
            headers=headers,
            data=json.dumps(data, ensure_ascii=False),
            timeout=settings.request_timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"].get("tool_calls")
    except Exception as exc:
        logger.error("Function Calling LLM failed: %s", exc)
        return None


def intent_recall(query, trace_id):
    if not os.getenv("INTENT_URL"):
        return _mock_intent_recall(query)

    headers = {"Content-Type": "application/json"}
    data = {"query": query, "trace_id": trace_id or str(uuid.uuid1())}
    try:
        response = requests.post(
            url=settings.intent_url,
            headers=headers,
            data=json.dumps(data, ensure_ascii=False),
            timeout=settings.request_timeout,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.error("Intent recall failed: %s", exc)
        return _mock_intent_recall(query)


def predict(query, trace_id):
    start = time.time()
    try:
        intent_rec = intent_recall(query, trace_id)
        results = str(intent_rec.get("data", "")).split(",")
        scores = [float(item) for item in str(intent_rec.get("score", "0")).split(",") if item]
        max_score = max(scores or [0.0])
        logger.info("Intent recall topk=%s cost=%.3fs", intent_rec.get("data"), time.time() - start)

        if not results or (results[0] == "3" and max_score > MAX_CONF):
            return f"{UNKNOWN_INTENT}-{EMPTY_SLOT}"

        now_tool = []
        for intent_id in results:
            func = id2func.get(intent_id)
            now_tool.extend(tool_map.get(func, []))

        messages = [
            {"role": "system", "content": prompts.NLU_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        tool_calls = send_messages(messages, now_tool)
        if not tool_calls:
            return _mock_nlu(query)
        return intent_slot(tool_calls, func2name, slot_map)
    except Exception as exc:
        logger.error("NLU predict failed: %s", exc)
        return _mock_nlu(query)


async def inference(request: Request):
    begin = time.time()
    json_info = await request.json()
    query = json_info.get("query", "")
    enable_dm = json_info.get("enable_dm", True)
    trace_id = json_info.get("trace_id", "1")

    nlu = predict(query, trace_id)
    intent, slots = _parse_nlu(nlu)
    intent_id = name2id.get(intent, "")
    func_name = id2func.get(intent_id, "Unknown")

    response = {
        "query": query,
        "trace_id": trace_id,
        "intent": intent,
        "intent_id": intent_id,
        "function": func_name,
        "slots": slots,
    }

    if enable_dm and func_name != "Unknown":
        for name in ["weather", "music", "maps"]:
            dm_result = await DMFactory.get(name)(func_name, query, slots)
            if dm_result:
                tool_response, nlg = dm_result
                response["tool"] = tool_response
                response["nlg"] = nlg
                break

    response["cost"] = time.time() - begin
    return response


if app:
    app.post("/chatnlu-server/v1")(inference)


def _parse_nlu(nlu):
    items = str(nlu).split("-")
    intent = items[0] if items else UNKNOWN_INTENT
    slots_str = "-".join(items[1:]) if len(items) > 1 else EMPTY_SLOT
    if slots_str == EMPTY_SLOT:
        return intent, {}

    slots = {}
    for item in slots_str.split(","):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        slots[key] = value
    return intent, slots


def _mock_intent_recall(query):
    for intent_id, func in id2func.items():
        if "weather" in func.lower() and "天气" in query:
            return {"data": intent_id, "score": "0.90"}
        if "music" in func.lower() and any(word in query for word in ["播放", "歌曲", "音乐"]):
            return {"data": intent_id, "score": "0.90"}
        if "map" in func.lower() and any(word in query for word in ["导航", "路线", "怎么走"]):
            return {"data": intent_id, "score": "0.90"}
    return {"data": "3", "score": "0.99"}


def _mock_nlu(query):
    if "天气" in query:
        return "天气查询-City:北京" if "北京" in query else "天气查询-City:"
    if any(word in query for word in ["播放", "歌曲", "音乐"]):
        return "音乐播放-Singer:周杰伦" if "周杰伦" in query else "音乐播放-Singer:"
    return f"{UNKNOWN_INTENT}-{EMPTY_SLOT}"


if __name__ == "__main__":
    if uvicorn is None:
        raise RuntimeError("Install runtime dependencies first: pip install -r requirements-runtime.txt")
    uvicorn.run(app, host="0.0.0.0", port=8009, workers=1)
