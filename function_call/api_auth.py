"""Authentication helpers for OpenAI-compatible HTTP APIs."""

from __future__ import annotations


def bearer_authorization(api_key: str) -> str:
    """Accept both a raw provider key and a preformatted Bearer value."""

    value = api_key.strip()
    if not value:
        return ""
    if value.lower().startswith("bearer "):
        return value
    return f"Bearer {value}"
