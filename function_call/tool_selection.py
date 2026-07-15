"""Utilities for preparing a valid OpenAI-compatible tool catalog."""

from __future__ import annotations

COMPACT_DEMO_TOOLS = {
    "Query_Weather": ("Query weather.", {"City": "city", "Date": "date"}),
    "Query_Timely_Weather": ("Query current weather.", {"City": "city"}),
    "Search_Music": ("Find music by artist or song.", {"Singer": "artist", "Song": "song"}),
    "Play_Online_Music": ("Play online music.", {"Singer": "artist", "Song": "song"}),
    "Go_POI": ("Navigate to a destination.", {"POI": "destination"}),
    "Go_Company": ("Navigate to the saved company address.", {}),
    "Add_Via": ("Add a navigation waypoint.", {"POI": "destination", "Via": "waypoint"}),
}


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


def build_compact_demo_tool_map() -> dict[str, list[dict]]:
    """Return minimal, executable schemas for the public demo tool bridge."""
    return {
        name: [_compact_tool(name, description, properties)]
        for name, (description, properties) in COMPACT_DEMO_TOOLS.items()
    }


def select_ranked_demo_tools(
    ranked_functions: list[str],
    top_score: float,
    navigation_context: bool = False,
) -> list[str]:
    """Keep BERT recall broad while constraining FC to runnable demo functions."""
    runnable = list(COMPACT_DEMO_TOOLS)
    selected = _dedupe(name for name in ranked_functions if name in COMPACT_DEMO_TOOLS)
    if navigation_context:
        selected = _dedupe([*selected, "Go_POI", "Add_Via", "Go_Company"])
    if not selected:
        return []
    return selected[: 1 if top_score >= 0.98 else 3]


def schema_payload_chars(tools: list[dict]) -> int:
    """Stable schema-size metric for traces and regression tests."""
    import json

    return len(json.dumps(tools, ensure_ascii=False, separators=(",", ":")))


def _compact_tool(name: str, description: str, properties: dict[str, str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    field: {"type": "string", "description": field_description}
                    for field, field_description in properties.items()
                },
            },
        },
    }


def _dedupe(names) -> list[str]:
    return list(dict.fromkeys(names))
