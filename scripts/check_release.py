# -*- coding: utf-8 -*-

"""Check whether the repository is safe to upload to GitHub."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCKED_SUFFIXES = {".bin", ".ckpt", ".pth", ".safetensors"}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "dist", "build", "log"}
MAX_FILE_MB = 50
NOISY_ROOT_FILES = {"test.py", "test_api.py", "test_fc.py", "test_fc2.py"}
LOCAL_MODEL_DIRS = (Path("train/pretrained"), Path("train/saved"))
REQUIRED_FILES = [
    "README.md",
    ".env.example",
    ".gitignore",
    "pyproject.toml",
    "docs/entrypoints.md",
    "docs/demo-walkthrough.md",
    "docs/legacy-runtime-flow.md",
    "docs/function-schema-report.md",
    "docs/model-experiment-results.md",
    "scripts/check_project.py",
    "scripts/check_env.py",
    "scripts/check_text_quality.py",
]


def iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file():
            yield path


def collect_release_status(root: Path = ROOT, max_file_mb: int = MAX_FILE_MB) -> dict[str, object]:
    blocked_model_files: list[str] = []
    oversized_files: list[str] = []
    local_model_files: list[str] = []
    max_bytes = max_file_mb * 1024 * 1024

    for path in iter_files(root):
        relative = path.relative_to(root).as_posix()
        relative_path = path.relative_to(root)
        if any(local_dir in relative_path.parents for local_dir in LOCAL_MODEL_DIRS):
            if path.suffix.lower() in BLOCKED_SUFFIXES:
                local_model_files.append(relative)
            continue
        if path.suffix.lower() in BLOCKED_SUFFIXES:
            blocked_model_files.append(relative)
        if path.stat().st_size > max_bytes:
            oversized_files.append(relative)

    missing_required = [name for name in REQUIRED_FILES if not (root / name).exists()]
    noisy_root_files = [name for name in sorted(NOISY_ROOT_FILES) if (root / name).exists()]

    return {
        "blocked_model_files": blocked_model_files,
        "oversized_files": oversized_files,
        "local_model_files": local_model_files,
        "missing_required": missing_required,
        "noisy_root_files": noisy_root_files,
        "ok": not (blocked_model_files or oversized_files or missing_required or noisy_root_files),
    }


def render_status(status: dict[str, object]) -> str:
    lines = ["release_readiness:"]
    for key in ["blocked_model_files", "oversized_files", "local_model_files", "missing_required", "noisy_root_files"]:
        values = status.get(key, [])
        assert isinstance(values, list)
        if values:
            lines.append(f"- {key}: {', '.join(values)}")
        else:
            lines.append(f"- {key}: none")
    lines.append(f"- ok: {status['ok']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check GitHub release readiness.")
    parser.add_argument("--strict", action="store_true", help="fail when release issues are found")
    args = parser.parse_args()

    status = collect_release_status()
    print(render_status(status))
    if args.strict and not status["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
