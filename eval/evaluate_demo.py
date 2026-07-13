# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from voice_agent_mcp.agent import DialogueAgent


CASES = Path(__file__).with_name("demo_cases.jsonl")


def main() -> int:
    agent = DialogueAgent()
    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line]
    total = len(cases)
    intent_ok = 0
    function_ok = 0
    slot_ok = 0

    for case in cases:
        final = agent.handle_as_dicts(case["query"], sender_id="eval")[-1]
        intent_ok += final["intent"] == case["intent"]
        function_ok += final["function"] == case["function"]
        slot_ok += all(final["slots"].get(k) == v for k, v in case["slots"].items())

    print(f"cases: {total}")
    print(f"intent_acc: {intent_ok / total:.2%}")
    print(f"function_acc: {function_ok / total:.2%}")
    print(f"slot_acc: {slot_ok / total:.2%}")
    return 0 if intent_ok == function_ok == slot_ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
