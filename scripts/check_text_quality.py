# -*- coding: utf-8 -*-

"""Detect obvious mojibake in files that readers see first on GitHub."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = [
    ROOT / "README.md",
    ROOT / ".env.example",
    ROOT / "docs",
    ROOT / "examples",
    ROOT / "scripts",
]
TEXT_SUFFIXES = {".md", ".py", ".txt", ".toml", ".example"}
MOJIBAKE_MARKERS = (
    "\ufffd",
    "\u00c3",
    "\u00c2",
    "\u9225",
    "\u6d93",
    "\u93c4",
    "\u93b7",
    "\u9356",
    "\u6fb6",
    "\u95c2",
    "\u9427",
)


def iter_text_files(paths: list[Path] | None = None):
    for path in paths or DEFAULT_PATHS:
        if path.is_file():
            yield path
            continue
        if path.is_dir():
            for item in path.rglob("*"):
                if item.is_file() and item.suffix in TEXT_SUFFIXES and "__pycache__" not in item.parts:
                    yield item


def find_mojibake(paths: list[Path] | None = None) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in iter_text_files(paths):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append({"path": path, "line": 0, "marker": "decode_error", "text": ""})
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            marker = next((item for item in MOJIBAKE_MARKERS if item in line), "")
            if marker:
                findings.append({"path": path, "line": line_no, "marker": marker, "text": line.strip()[:120]})
    return findings


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Check visible project text for mojibake.")
    parser.add_argument("--strict", action="store_true", help="fail when mojibake markers are found")
    args = parser.parse_args()

    findings = find_mojibake()
    if not findings:
        print("text_quality: ok")
        return

    print(f"text_quality: {len(findings)} issue(s)")
    for item in findings[:50]:
        path = Path(item["path"]).relative_to(ROOT)
        print(f"- {path}:{item['line']} marker={item['marker']} text={item['text']}")
    if len(findings) > 50:
        print(f"- ... {len(findings) - 50} more")
    if args.strict:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
