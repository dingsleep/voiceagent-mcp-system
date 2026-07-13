# -*- coding: utf-8 -*-

"""Report runtime environment readiness without contacting external services."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

LEGACY_GROUPS = {
    "llm_endpoint": ("BASE_URL", "LLM_BASE_URL"),
    "llm_api_key": ("API_KEY", "LLM_API_KEY"),
    "llm_model": ("LLM_MODEL_ID", "LLM_MODEL"),
    "socketio_entry": ("ENTRY_URL",),
}


def parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def collect_env_status(root: Path = ROOT) -> dict[str, object]:
    file_values = parse_dotenv(root / ".env")
    merged = {**os.environ, **file_values}
    missing = [
        name
        for name, aliases in LEGACY_GROUPS.items()
        if not any(merged.get(alias) for alias in aliases)
    ]
    configured = {
        name: next((alias for alias in aliases if merged.get(alias)), "")
        for name, aliases in LEGACY_GROUPS.items()
    }
    return {
        "env_file_exists": (root / ".env").exists(),
        "example_file_exists": (root / ".env.example").exists(),
        "configured": configured,
        "missing_legacy_groups": missing,
    }


def render_status(status: dict[str, object]) -> str:
    configured = status["configured"]
    assert isinstance(configured, dict)
    lines = [
        "Environment readiness",
        f"- .env exists: {status['env_file_exists']}",
        f"- .env.example exists: {status['example_file_exists']}",
        "- legacy chain variables:",
    ]
    for name, source in configured.items():
        lines.append(f"  - {name}: {'ok via ' + source if source else 'missing'}")
    missing = status["missing_legacy_groups"]
    assert isinstance(missing, list)
    if missing:
        lines.append(f"- missing for full legacy chain: {', '.join(missing)}")
    else:
        lines.append("- missing for full legacy chain: none")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check local runtime environment variables.")
    parser.add_argument("--strict", action="store_true", help="fail when legacy variables are missing")
    args = parser.parse_args()

    status = collect_env_status()
    print(render_status(status))
    if args.strict and status["missing_legacy_groups"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
