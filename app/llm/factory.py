"""Pick the LLM provider named by the LLM_PROVIDER setting."""

from __future__ import annotations

from pydantic import SecretStr

from app.config import Settings
from app.llm.base import LLMProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.groq_provider import GroqProvider


def _require(key: SecretStr | None, name: str) -> str:
    value = key.get_secret_value().strip() if key else ""
    if not value:
        raise ValueError(f"{name} is not set. Add it to your .env file.")
    return value


def get_llm(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "groq":
        return GroqProvider(_require(settings.groq_api_key, "GROQ_API_KEY"), settings.groq_model)
    if settings.llm_provider == "gemini":
        return GeminiProvider(
            _require(settings.gemini_api_key, "GEMINI_API_KEY"), settings.gemini_model
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
