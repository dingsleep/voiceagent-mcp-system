"""Central runtime settings for the legacy dialogue chain."""

from __future__ import annotations

import os
from dataclasses import dataclass


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def env_any(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


@dataclass(frozen=True)
class Settings:
    api_key: str = env_any("API_KEY", "LLM_API_KEY")
    base_url: str = env_any("BASE_URL", "LLM_BASE_URL")
    bot_url: str = env_any("BOT_URL", "BASE_URL", "LLM_BASE_URL")
    llm_model: str = env_any("LLM_MODEL_ID", "LLM_MODEL", default="mock-model")
    intent_url: str = env("INTENT_URL", "http://127.0.0.1:8008/intent-server/v1")
    nlu_url: str = env("NLU_URL", "http://127.0.0.1:8009/chatnlu-server/v1")
    reject_url: str = env("REJECT_URL", "http://127.0.0.1:8007/reject-server/v1")
    redis_host: str = env("REDIS_HOST", "127.0.0.1")
    redis_port: int = int(env("REDIS_PORT", "6379"))
    redis_db: int = int(env("REDIS_DB", "0"))
    request_timeout: float = float(env("REQUEST_TIMEOUT", "5"))


settings = Settings()
