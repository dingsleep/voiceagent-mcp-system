"""Utilities for preparing a valid OpenAI-compatible tool catalog."""

from __future__ import annotations


def select_canonical_tool(items: list[dict]) -> dict:
    """Choose the richest schema when a legacy catalog repeats one function."""

    if not items:
        raise ValueError("At least one tool schema is required")

    return max(
        items,
        key=lambda item: (
            len(item["function"].get("parameters", {}).get("properties", {})),
            len(item["function"].get("description", "")),
        ),
    )


def build_unique_tool_map(tools: list[dict]) -> dict[str, list[dict]]:
    """Group a legacy catalog by function name and retain one schema per name."""

    candidates: dict[str, list[dict]] = {}
    for item in tools:
        candidates.setdefault(item["function"]["name"], []).append(item)

    return {
        function_name: [select_canonical_tool(items)]
        for function_name, items in candidates.items()
    }
