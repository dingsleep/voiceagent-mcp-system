# -*- coding: utf-8 -*-

"""Evaluate the runnable Agent without hiding remote NLU fallbacks."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from voice_agent_mcp.agent import DialogueAgent
from voice_agent_mcp.nlu_backends import RuleNluBackend, build_nlu_backend
from voice_agent_mcp.runtime import load_local_env

CASES = Path(__file__).with_name("demo_cases.jsonl")


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate_cases(agent: DialogueAgent, cases: list[dict], backend_mode: str) -> dict:
    results: list[dict] = []
    fallback_reasons: Counter[str] = Counter()
    latencies: list[int] = []
    intent_ok = function_ok = slot_ok = remote_attempts = remote_used = 0

    for index, case in enumerate(cases):
        sender_id = case.get("sender_id", f"eval-{index}")
        final = agent.handle_as_dicts(case["query"], sender_id=sender_id, trace_id=f"eval-{index}")[-1]
        metadata = final["metadata"]
        intent_match = final["intent"] == case["intent"]
        function_match = final["function"] == case["function"]
        slots_match = all(final["slots"].get(key) == value for key, value in case["slots"].items())
        intent_ok += intent_match
        function_ok += function_match
        slot_ok += slots_match

        used_backend = metadata.get("nlu_backend", "not_used")
        if backend_mode == "remote" and used_backend != "not_used":
            remote_attempts += 1
        if used_backend == "remote":
            remote_used += 1
        if reason := metadata.get("fallback_reason"):
            fallback_reasons[reason] += 1
        if isinstance(metadata.get("total_latency_ms"), int):
            latencies.append(metadata["total_latency_ms"])

        results.append(
            {
                "case": index,
                "expected": {key: case[key] for key in ("intent", "function", "slots")},
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
        "intent_accuracy": _ratio(intent_ok, total),
        "function_accuracy": _ratio(function_ok, total),
        "slot_accuracy": _ratio(slot_ok, total),
        "all_expected_match": intent_ok == function_ok == slot_ok == total,
        "remote_attempts": remote_attempts,
        "remote_used": remote_used,
        "remote_success_rate": _ratio(remote_used, remote_attempts),
        "fallbacks": dict(sorted(fallback_reasons.items())),
        "latency_ms": _latency_summary(latencies),
        "results": results,
    }


def render_report(report: dict) -> str:
    lines = [
        f"backend_mode: {report['backend_mode']}",
        f"cases: {report['cases']}",
        f"intent_acc: {report['intent_accuracy']:.2%}",
        f"function_acc: {report['function_accuracy']:.2%}",
        f"slot_acc: {report['slot_accuracy']:.2%}",
        f"remote_attempts: {report['remote_attempts']}",
        f"remote_used: {report['remote_used']}",
        f"remote_success_rate: {report['remote_success_rate']:.2%}",
        "latency_ms: " + ", ".join(f"{key}={value}" for key, value in report["latency_ms"].items()),
    ]
    if report["fallbacks"]:
        lines.append("fallbacks:")
        lines.extend(f"  {reason}: {count}" for reason, count in report["fallbacks"].items())
    return "\n".join(lines)


def _ratio(value: int, total: int) -> float:
    return value / total if total else 0.0


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
    return DialogueAgent(nlu_backend=build_nlu_backend("remote"))


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
