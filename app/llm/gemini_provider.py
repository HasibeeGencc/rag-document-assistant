"""Google Gemini: backup provider, selected with LLM_PROVIDER=gemini."""

from __future__ import annotations

from typing import Any

from app.llm.base import LLMError

TEMPERATURE = 0.1


class GeminiProvider:
    def __init__(self, api_key: str, model: str, client: Any = None):
        if client is None:
            from google import genai

            client = genai.Client(api_key=api_key)
        self._client = client
        self.model = model

    def complete(self, system: str, user: str) -> str:
        from google.genai import types

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system, temperature=TEMPERATURE
                ),
            )
        except Exception as exc:
            raise LLMError(f"Gemini request failed ({type(exc).__name__})") from exc
        return (response.text or "").strip()
