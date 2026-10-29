"""Groq: fast hosted open models, with a free tier."""

from __future__ import annotations

from typing import Any

from app.llm.base import LLMError

# Low temperature = less creative, more faithful to the context. That is what
# we want for answering from documents.
TEMPERATURE = 0.1


class GroqProvider:
    def __init__(self, api_key: str, model: str, client: Any = None):
        if client is None:
            from groq import Groq

            client = Groq(api_key=api_key)
        self._client = client
        self.model = model

    def complete(self, system: str, user: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=TEMPERATURE,
            )
        except Exception as exc:
            # Only the error type goes into the message: the SDK's own text
            # can include request details we don't want in logs.
            raise LLMError(f"Groq request failed ({type(exc).__name__})") from exc
        return (response.choices[0].message.content or "").strip()
