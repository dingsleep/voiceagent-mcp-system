# -*- coding: utf-8 -*-

"""Inspect and validate the large Function Calling schema library."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from function_call.function import tools1


ROOT = Path(__file__).resolve().parents[1]
CLASS_FILE = ROOT / "config" / "class.txt"
SLOT_FILE = ROOT / "config" / "slot_intent.json"

DOMAIN_RULES = {
    "driving_assistance": [
        "AutoHold",
        "Engine_AutoStop",
        "Driving_Mode",
        "Cruise",
        "Electronic_Eye",
        "Safety_Alarm",
        "Speed",
    ],
    "climate_control": [
        "Air_Condition",
        "AC",
        "Cooling",
        "Heating",
        "Wind",
        "Defog",
        "Circulation",
        "Air_Cleaner",
    ],
    "seat_control": ["Seat", "Steer"],
    "vehicle_body": [
        "Window",
        "Door",
        "Trunk",
        "Sunroof",
        "Dormer",
        "Sunshade",
        "Light",
        "Beam",
        "Headlamp",
        "HEAPLAMP",
        "Wiper",
        "Mirror",
        "DashCam",
        "Wireless_Charge",
        "Surround_View",
    ],
    "navigation_map": [
        "Nav",
        "POI",
        "Route",
        "Map",
        "Company",
        "Home",
        "Traffic",
        "Condition",
        "Where",
        "Location",
        "Congestion",
        "High_Way",
        "Limit_Line",
        "Meeting_Place",
        "Group",
        "Via",
    ],
    "media": ["Media", "Music", "Radio", "Play", "Audio", "Video", "lyrics", "Timbre", "KTV"],
    "phone_connectivity": ["Phone", "Call", "Number", "Bluetooth", "Wifi", "Connection"],
    "system_settings": [
        "System",
        "Config",
        "App",
        "Mini_App",
        "Brightness",
        "Sound",
        "Volume",
        "Desktop",
        "Hud",
        "HUD",
        "Help",
        "Feedback",
        "Owner_Service",
        "Personal_Center",
        "APP",
        "Message",
        "Order",
        "ScreenCast",
        "Card",
    ],
    "voice_assistant": [
        "Answer_Words",
        "Voice",
        "Wakeup",
        "Continuous_Dialogue",
        "Free_Wakeup",
        "Interactive_Learning",
        "Skill_Instruction",
        "Online_NLU",
        "Speech",
    ],
    "scene_mode": ["Scene", "Snooze", "Preset"],
    "vehicle_service": ["Complains", "Suggestions", "Order", "Current_Content", "Send_Record", "Face"],
    "weather_info": ["Weather", "Humidity", "Air_Quality", "Sunrise", "Sunset"],
    "life_service": ["News", "Oil_Price", "Station"],
    "calendar_schedule": ["Calendar", "Schedule", "Date"],
    "dialog_control": ["Confirm", "Cancel", "Back", "Quit", "Continue", "Select", "Reject", "Unknown"],
}


def build_catalog() -> dict[str, Any]:
    names = [tool_name(item) for item in tools1]
    duplicates = {name: count for name, count in Counter(names).items() if count > 1}
    duplicate_definitions = build_duplicate_definitions(tools1, duplicates)
    duplicate_analysis = build_duplicate_analysis(tools1, duplicates)
    domains = Counter(classify_domain(name) for name in names)
    prefixes = Counter(name.split("_", 1)[0] for name in names if name)
    configured_functions = load_configured_functions()
    schema_slots = load_slot_config()
    issues = validate_tools(tools1, configured_functions, schema_slots)

    return {
        "total_tools": len(names),
        "unique_tools": len(set(names)),
        "duplicate_tools": len(names) - len(set(names)),
        "duplicates": dict(sorted(duplicates.items())),
        "duplicate_definitions": duplicate_definitions,
        "duplicate_analysis": duplicate_analysis,
        "domains": dict(sorted(domains.items())),
        "prefixes": dict(sorted(prefixes.items())),
        "configured_functions": len(configured_functions),
        "tools_missing_from_class_config": sorted(set(names) - configured_functions),
        "class_config_missing_from_tools": sorted(configured_functions - set(names)),
        "validation": issues,
    }


def validate_tools(
    tools: list[dict[str, Any]], configured_functions: set[str], slot_config: dict[str, Any]
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    seen: defaultdict[str, int] = defaultdict(int)

    for index, item in enumerate(tools):
        location = f"tools1[{index}]"
        if not isinstance(item, dict):
            issues.append(issue(location, "invalid_tool", "tool definition must be a dict"))
            continue
        if item.get("type") != "function":
            issues.append(issue(location, "invalid_type", "type must be 'function'"))

        function = item.get("function")
        if not isinstance(function, dict):
            issues.append(issue(location, "missing_function", "function must be a dict"))
            continue

        name = function.get("name")
        if not isinstance(name, str) or not name:
            issues.append(issue(location, "missing_name", "function.name is required"))
            continue

        seen[name] += 1
        current = f"{location}:{name}"
        if not isinstance(function.get("description"), str) or not function["description"].strip():
            issues.append(issue(current, "missing_description", "description is required"))

        parameters = function.get("parameters")
        if not isinstance(parameters, dict):
            issues.append(issue(current, "missing_parameters", "parameters must be a dict"))
            continue
        if parameters.get("type") != "object":
            issues.append(issue(current, "invalid_parameters_type", "parameters.type must be object"))

        properties = parameters.get("properties", {})
        if not isinstance(properties, dict):
            issues.append(issue(current, "invalid_properties", "parameters.properties must be a dict"))
            properties = {}

        required = parameters.get("required", [])
        if required and not isinstance(required, list):
            issues.append(issue(current, "invalid_required", "required must be a list"))
            required = []

        missing_required = [field for field in required if field not in properties]
        for field in missing_required:
            issues.append(issue(current, "required_not_in_properties", f"{field} missing in properties"))

        for field, schema in properties.items():
            if not isinstance(schema, dict):
                issues.append(issue(current, "invalid_property_schema", f"{field} schema must be a dict"))
                continue
            if "type" not in schema:
                issues.append(issue(current, "missing_property_type", f"{field} missing type"))
            if "description" not in schema:
                issues.append(issue(current, "missing_property_description", f"{field} missing description"))

        if name not in configured_functions:
            issues.append(issue(current, "not_in_class_config", "function not listed in config/class.txt"))
        if name not in slot_config:
            issues.append(issue(current, "not_in_slot_config", "function not listed in config/slot_intent.json"))

    for name, count in seen.items():
        if count > 1:
            issues.append(issue(name, "duplicate_name", f"appears {count} times"))
    return issues


def build_duplicate_definitions(
    tools: list[dict[str, Any]], duplicates: dict[str, int]
) -> dict[str, list[dict[str, Any]]]:
    duplicate_definitions: dict[str, list[dict[str, Any]]] = {}
    for index, item in enumerate(tools):
        name = tool_name(item)
        if name not in duplicates:
            continue
        function = item.get("function", {})
        parameters = function.get("parameters", {})
        properties = parameters.get("properties", {})
        required = parameters.get("required", [])
        duplicate_definitions.setdefault(name, []).append(
            {
                "index": index,
                "domain": classify_domain(name),
                "property_names": sorted(properties.keys()) if isinstance(properties, dict) else [],
                "required": required if isinstance(required, list) else [],
                "description_length": len(function.get("description", "")),
            }
        )
    return dict(sorted(duplicate_definitions.items()))


def build_duplicate_analysis(
    tools: list[dict[str, Any]], duplicates: dict[str, int]
) -> dict[str, dict[str, Any]]:
    analysis: dict[str, dict[str, Any]] = {}
    for name in sorted(duplicates):
        definitions = [
            duplicate_signature(index, item)
            for index, item in enumerate(tools)
            if tool_name(item) == name
        ]
        fingerprints = {item["fingerprint"] for item in definitions}
        same_schema = len(fingerprints) == 1
        analysis[name] = {
            "same_schema": same_schema,
            "fingerprints": sorted(fingerprints),
            "definitions": definitions,
            "merge_hint": duplicate_merge_hint(name, definitions, same_schema),
        }
    return analysis


def duplicate_signature(index: int, item: dict[str, Any]) -> dict[str, Any]:
    function = item.get("function", {})
    parameters = function.get("parameters", {})
    properties = parameters.get("properties", {})
    required = parameters.get("required", [])
    normalized = {
        "parameters": parameters,
        "description": function.get("description", ""),
    }
    fingerprint = hashlib.sha256(
        json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]
    return {
        "index": index,
        "fingerprint": fingerprint,
        "required": sorted(required) if isinstance(required, list) else [],
        "properties": sorted(properties) if isinstance(properties, dict) else [],
        "description_length": len(function.get("description", "")),
    }


def duplicate_merge_hint(name: str, definitions: list[dict[str, Any]], same_schema: bool) -> str:
    if same_schema:
        return "safe_candidate: definitions have the same schema and description"
    property_sets = {tuple(item["properties"]) for item in definitions}
    required_sets = {tuple(item["required"]) for item in definitions}
    if len(property_sets) == 1 and len(required_sets) == 1:
        return "review_description: schema is aligned but descriptions differ"
    if name in {"Go_POI", "Search_Music", "Search_Radio"}:
        return "do_not_merge_yet: core intent with different slot contracts"
    return "manual_review: duplicate name has different slot contracts"


def render_markdown(catalog: dict[str, Any]) -> str:
    issue_counter = Counter(item["code"] for item in catalog["validation"])
    lines = [
        "# Function Schema Quality Report",
        "",
        "Generated with:",
        "",
        "```bash",
        "python -m function_call.schema_catalog --markdown docs/function-schema-report.md",
        "```",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Total tool definitions | {catalog['total_tools']} |",
        f"| Unique tool names | {catalog['unique_tools']} |",
        f"| Duplicate tool definitions | {catalog['duplicate_tools']} |",
        f"| Functions in class config | {catalog['configured_functions']} |",
        f"| Validation issues | {len(catalog['validation'])} |",
        "",
        "## Domain Distribution",
        "",
        "| Domain | Tools |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {count} |" for name, count in catalog["domains"].items())

    lines.extend(["", "## Duplicate Tool Names", "", "| Function | Count |", "| --- | ---: |"])
    if catalog["duplicates"]:
        lines.extend(f"| `{name}` | {count} |" for name, count in catalog["duplicates"].items())
    else:
        lines.append("| None | 0 |")

    lines.extend(["", "## Duplicate Definition Details", ""])
    for name, definitions in catalog["duplicate_definitions"].items():
        lines.append(f"### `{name}`")
        lines.append("")

    lines.extend(["", "## Duplicate Merge Analysis", "", "| Function | Same schema | Hint | Fingerprints |"])
    lines.append("| --- | --- | --- | --- |")
    if catalog["duplicate_analysis"]:
        for name, item in catalog["duplicate_analysis"].items():
            fingerprints = ", ".join(f"`{value}`" for value in item["fingerprints"])
            lines.append(f"| `{name}` | {item['same_schema']} | {item['merge_hint']} | {fingerprints} |")
    else:
        lines.append("| None | True | - | - |")
        lines.append("| Index | Domain | Required | Properties | Description chars |")
        lines.append("| ---: | --- | --- | --- | ---: |")
        for item in definitions:
            required = ", ".join(item["required"]) or "-"
            properties = ", ".join(item["property_names"]) or "-"
            lines.append(
                f"| {item['index']} | {item['domain']} | {required} | {properties} | {item['description_length']} |"
            )
        lines.append("")

    lines.extend(["", "## Validation Issue Types", "", "| Issue | Count |", "| --- | ---: |"])
    if issue_counter:
        lines.extend(f"| `{name}` | {count} |" for name, count in sorted(issue_counter.items()))
    else:
        lines.append("| None | 0 |")

    lines.extend(["", "## Sample Issues", ""])
    for item in catalog["validation"][:30]:
        lines.append(f"- `{item['code']}` at `{item['location']}`: {item['message']}")
    if len(catalog["validation"]) > 30:
        lines.append(f"- ... {len(catalog['validation']) - 30} more issues")

    lines.extend(
        [
            "",
            "## Config Coverage",
            "",
            "### Tools missing from `config/class.txt`",
            "",
        ]
    )
    if catalog["tools_missing_from_class_config"]:
        lines.extend(f"- `{name}`" for name in catalog["tools_missing_from_class_config"])
    else:
        lines.append("- None")

    lines.extend(["", "### Class config entries missing from tool schemas", ""])
    if catalog["class_config_missing_from_tools"]:
        lines.extend(f"- `{name}`" for name in catalog["class_config_missing_from_tools"])
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def tool_name(item: dict[str, Any]) -> str:
    function = item.get("function") if isinstance(item, dict) else None
    if not isinstance(function, dict):
        return ""
    return str(function.get("name", ""))


def classify_domain(name: str) -> str:
    for domain, tokens in DOMAIN_RULES.items():
        if any(token in name for token in tokens):
            return domain
    return "other"


def load_configured_functions() -> set[str]:
    functions: set[str] = set()
    if not CLASS_FILE.exists():
        return functions
    for line in CLASS_FILE.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(":")
        if len(parts) == 3:
            functions.add(parts[2])
    return functions


def load_slot_config() -> dict[str, Any]:
    if not SLOT_FILE.exists():
        return {}
    return json.loads(SLOT_FILE.read_text(encoding="utf-8"))


def issue(location: str, code: str, message: str) -> dict[str, str]:
    return {"location": location, "code": code, "message": message}


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Function Calling schemas.")
    parser.add_argument("--json", dest="json_path", help="write full catalog as JSON")
    parser.add_argument("--markdown", dest="markdown_path", help="write markdown report")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when validation issues remain",
    )
    args = parser.parse_args()

    catalog = build_catalog()
    print(f"total_tools: {catalog['total_tools']}")
    print(f"unique_tools: {catalog['unique_tools']}")
    print(f"duplicate_tools: {catalog['duplicate_tools']}")
    print(f"validation_issues: {len(catalog['validation'])}")
    print("domains:")
    for name, count in catalog["domains"].items():
        print(f"  {name}: {count}")

    if args.json_path:
        Path(args.json_path).write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown_path:
        Path(args.markdown_path).write_text(render_markdown(catalog), encoding="utf-8")
    if args.strict and catalog["validation"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
