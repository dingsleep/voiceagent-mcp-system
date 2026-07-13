# -*- coding: utf-8 -*-

"""Run the minimum checks before publishing the project."""

from __future__ import annotations

import subprocess
import sys
import tokenize
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "build", "dist"}
sys.path.insert(0, str(ROOT))


def compile_sources() -> bool:
    for path in ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            with tokenize.open(path) as source_file:
                compile(source_file.read(), str(path), "exec")
        except (SyntaxError, UnicodeDecodeError) as exc:
            print(exc, file=sys.stderr)
            return False
    return True


def main() -> int:
    if not compile_sources():
        return 1

    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        return 1

    env_result = subprocess.run(
        [sys.executable, "scripts/check_env.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(env_result.stdout.strip())
    if env_result.returncode != 0:
        print(env_result.stderr, file=sys.stderr)
        return env_result.returncode

    text_result = subprocess.run(
        [sys.executable, "scripts/check_text_quality.py", "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(text_result.stdout.strip())
    if text_result.returncode != 0:
        print(text_result.stderr, file=sys.stderr)
        return text_result.returncode

    release_result = subprocess.run(
        [sys.executable, "scripts/check_release.py", "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(release_result.stdout.strip())
    if release_result.returncode != 0:
        print(release_result.stderr, file=sys.stderr)
        return release_result.returncode

    data_result = subprocess.run(
        [sys.executable, "scripts/check_training_data.py", "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(data_result.stdout.strip())
    if data_result.returncode != 0:
        print(data_result.stderr, file=sys.stderr)
        return data_result.returncode

    smoke = subprocess.run(
        [sys.executable, "-m", "voice_agent_mcp.cli", "--query", "北京明天天气怎么样"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(smoke.stdout.strip())
    if smoke.returncode != 0:
        print(smoke.stderr, file=sys.stderr)
        return smoke.returncode
    eval_result = subprocess.run(
        [sys.executable, "eval/evaluate_demo.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(eval_result.stdout.strip())
    if eval_result.returncode != 0:
        print(eval_result.stderr, file=sys.stderr)
        return eval_result.returncode
    schema_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "function_call.schema_catalog",
            "--markdown",
            "docs/function-schema-report.md",
            "--json",
            "docs/function-schema-catalog.json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(schema_result.stdout.strip())
    if schema_result.returncode != 0:
        print(schema_result.stderr, file=sys.stderr)
        return schema_result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
