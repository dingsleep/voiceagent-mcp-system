"""Entrypoint-only environment loading for local runs."""

from pathlib import Path

from dotenv import load_dotenv


def load_local_env() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
