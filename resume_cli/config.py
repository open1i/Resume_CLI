"""Central configuration loaded once from environment / .env file."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

__all__ = ["config"]


class _Config:
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    base_url: str | None = os.getenv("OPENAI_BASE_URL") or None
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    timeout: float = float(os.getenv("AI_TIMEOUT", "30"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


config = _Config()
