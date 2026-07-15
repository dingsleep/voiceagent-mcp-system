# -*- coding: utf-8 -*-

"""Evaluate the runnable Agent without hiding remote NLU fallbacks."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from voice_agent_mcp.agent import DialogueAgent
from voice_agent_mcp.live_tools import build_live_registry
from voice_agent_mcp.nlu_backends import RuleNluBackend, build_nlu_backend
from voice_agent_mcp.reject_backends import RemoteRejectBackend
from voice_agent_mcp.runtime import load_local_env

CASES = Path(__file__).with_name("demo_cases.jsonl")


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate_cases(agent: DialogueAgent, cases: list[dict], backend_mode: str) -> dict:
    results: list[dict] = []
    fallback_reasons: Counter[str] = Counter()
    latencies: list[int] = []
    stage_latencies: dict[str, list[int]] = {
        "reject": [],
        "intent_bert": [],
        "deepseek_fc": [],
        "tool": [],
    }
    function_call_tokens: dict[str, list[int]] = {
        "prompt_tokens": [],
        "completion_tokens": [],
        "total_tokens": [],
    }
    chat_tokens: dict[str, list[int]] = {
        "prompt_tokens": [],
        "completion_tokens": [],
        "total_tokens": [],
    }
    intent_ok = function_ok = slot_ok = remote_attempts = remote_used = 0
    intent_checked = function_checked = slot_checked = remote_fallbacks = 0

    for index, case in enumerate(cases):
        sender_id = case.get("sender_id", f"eval-{index}")
        final = agent.handle_as_dicts(case["query"], sender_id=sender_id, trace_id=f"eval-{index}")[-1]
        metadata = final["metadata"]
        intent_match = final["intent"] == case.get("intent") if "intent" in case else None
        function_match = final["function"] == case.get("function") if "function" in case else None
        slots_match = (
            all(final["slots"].get(key) == value for key, value in case.get("slots", {}).items())
            if "slots" in case
            else None
        )
        if intent_match is not None:
            intent_checked += 1
            intent_ok += intent_match
        if function_match is not None:
            function_checked += 1
            function_ok += function_match
        if slots_match is not None:
            slot_checked += 1
            slot_ok += slots_match

        used_backend = metadata.get("nlu_backend", "not_used")
        reason = metadata.get("fallback_reason", "")
        remote_attempted = used_backend == "remote" or reason.startswith(("remote_fallback:", "remote_error:"))
        if backend_mode == "remote" and remote_attempted:
            remote_attempts += 1
        if used_backend == "remote":
            remote_used += 1
        if reason:
            fallback_reasons[reason] += 1
            if backend_mode == "remote" and remote_attempted:
                remote_fallbacks += 1
        if isinstance(metadata.get("total_latency_ms"), int):
            latencies.append(metadata["total_latency_ms"])
        _append_stage_latencies(stage_latencies, metadata)
        _append_token_usage(function_call_tokens, metadata.get("nlu_trace", {}).get("function_call", {}).get("usage", {}))
        _append_token_usage(chat_tokens, metadata.get("chat_trace", {}).get("usage", {}))

        results.append(
            {
                "case": index,
                "id": case.get("id", f"case-{index}"),
                "group": case.get("group", "default"),
                "query": case["query"],
                "expected": {key: case[key] for key in ("intent", "function", "slots") if key in case},
                "actual": {
                    "intent": final["intent"],
                    "function": final["function"],
                    "slots": final["slots"],
                },
                "matches": {"intent": intent_match, "function": function_match, "slots": slots_match},
                "runtime": metadata,
            }
        )

    total = len(cases)
    return {
        "backend_mode": backend_mode,
        "cases": total,
        "intent_accuracy": _ratio(intent_ok, intent_checked),
        "function_accuracy": _ratio(function_ok, function_checked),
        "slot_accuracy": _ratio(slot_ok, slot_checked),
        "expected_checks": {
            "intent": intent_checked,
            "function": function_checked,
            "slots": slot_checked,
        },
        "all_expected_match": all((
            intent_ok == intent_checked,
            function_ok == function_checked,
            slot_ok == slot_checked,
        )),
        "remote_attempts": remote_attempts,
        "remote_used": remote_used,
        "remote_success_rate": _ratio(remote_used, remote_attempts),
        "remote_fallbacks": remote_fallbacks,
        "remote_fallback_rate": _ratio(remote_fallbacks, remote_attempts),
        "fallbacks": dict(sorted(fallback_reasons.items())),
        "latency_ms": _latency_summary(latencies),
        "stage_latency_ms": {name: _latency_summary(values) for name, values in stage_latencies.items()},
        "function_call_tokens": _token_summary(function_call_tokens),
        "chat_tokens": _token_summary(chat_tokens),
        "results": results,
    }


def render_report(report: dict) -> str:
    lines = [
        f"backend_mode: {report['backend_mode']}",
        f"cases: {report['cases']}",
        f"intent_acc: {_format_accuracy(report['intent_accuracy'], report['expected_checks']['intent'])}",
        f"function_acc: {_format_accuracy(report['function_accuracy'], report['expected_checks']['function'])}",
        f"slot_acc: {_format_accuracy(report['slot_accuracy'], report['expected_checks']['slots'])}",
        f"remote_attempts: {report['remote_attempts']}",
        f"remote_used: {report['remote_used']}",
        f"remote_success_rate: {report['remote_success_rate']:.2%}",
        f"remote_fallback_rate: {report['remote_fallback_rate']:.2%}",
        "latency_ms: " + ", ".join(f"{key}={value}" for key, value in report["latency_ms"].items()),
        "stage_latency_ms:",
    ]
    lines.extend(
        f"  {stage}: " + ", ".join(f"{key}={value}" for key, value in summary.items())
        for stage, summary in report["stage_latency_ms"].items()
    )
    lines.append("function_call_tokens: " + ", ".join(f"{key}={value}" for key, value in report["function_call_tokens"].items()))
    lines.append("chat_tokens: " + ", ".join(f"{key}={value}" for key, value in report["chat_tokens"].items()))
    if report["fallbacks"]:
        lines.append("fallbacks:")
        lines.extend(f"  {reason}: {count}" for reason, count in report["fallbacks"].items())
    return "\n".join(lines)


def _ratio(value: int, total: int) -> float:
    return value / total if total else 0.0


def _format_accuracy(value: float, checked: int) -> str:
    return f"{value:.2%}" if checked else "n/a"


def _latency_summary(values: list[int]) -> dict:
    if not values:
        return {"count": 0, "min": 0, "p50": 0, "p95": 0, "max": 0}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min": ordered[0],
        "p50": _percentile(ordered, 0.50),
        "p95": _percentile(ordered, 0.95),
        "max": ordered[-1],
    }


def _token_summary(values_by_name: dict[str, list[int]]) -> dict:
    return {
        name: {
            "count": len(values),
            "total": sum(values),
            "p50": _percentile(sorted(values), 0.50) if values else 0,
            "p95": _percentile(sorted(values), 0.95) if values else 0,
        }
        for name, values in values_by_name.items()
    }


def _append_stage_latencies(stage_latencies: dict[str, list[int]], metadata: dict) -> None:
    reject = metadata.get("reject_trace", {})
    nlu_trace = metadata.get("nlu_trace", {})
    function_call = nlu_trace.get("function_call", {})
    tool_trace = metadata.get("tool_trace", {})
    _append_number(stage_latencies["reject"], reject.get("latency_ms"))
    _append_number(stage_latencies["intent_bert"], nlu_trace.get("intent_recall", {}).get("latency_ms"))
    _append_number(stage_latencies["deepseek_fc"], function_call.get("latency_ms"))
    _append_number(stage_latencies["tool"], tool_trace.get("latency_ms"))


def _append_token_usage(values_by_name: dict[str, list[int]], usage: dict) -> None:
    for name, values in values_by_name.items():
        _append_number(values, usage.get(name))


def _append_number(values: list[int], value: object) -> None:
    if isinstance(value, int):
        values.append(value)


def _percentile(ordered: list[int], quantile: float) -> int:
    position = (len(ordered) - 1) * quantile
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower))


def _build_agent(backend_mode: str) -> DialogueAgent:
    if backend_mode == "rule":
        return DialogueAgent(nlu_backend=RuleNluBackend())
    load_local_env()
    tools = build_live_registry() if os.getenv("AMAP_MAPS_API_KEY") else None
    return DialogueAgent(
        tools=tools,
        nlu_backend=build_nlu_backend("remote"),
        reject_backend=RemoteRejectBackend(os.getenv("REJECT_URL", "http://127.0.0.1:8007/reject-server/v1")),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the runnable vehicle Agent.")
    parser.add_argument("--backend", choices=("rule", "remote"), default="rule")
    parser.add_argument("--case-file", type=Path, default=CASES)
    parser.add_argument("--report", type=Path, help="write the detailed JSON report to this local path")
    parser.add_argument("--allow-network", action="store_true", help="required before calling the remote NLU backend")
    parser.add_argument("--strict", action="store_true", help="fail when expected outputs mismatch or a remote fallback occurs")
    args = parser.parse_args(argv)

    if args.backend == "remote" and not args.allow_network:
        parser.error("remote evaluation requires --allow-network because it can call external model services")

    report = evaluate_cases(_build_agent(args.backend), load_cases(args.case_file), args.backend)
    print(render_report(report))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"report: {args.report}")

    failed = args.strict and (not report["all_expected_match"] or bool(report["fallbacks"]))
    if args.backend == "rule" and not report["all_expected_match"]:
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
