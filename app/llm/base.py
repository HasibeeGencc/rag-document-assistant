"""The interface every LLM provider implements.

The RAG pipeline only talks to this interface, so switching from Groq to
Gemini (or to a fake in tests) needs no changes to the pipeline.
"""

from typing import Protocol


class LLMError(Exception):
    """The LLM call failed (network, rate limit, bad key...)."""


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str:
        """Send a system prompt and a user message; return the reply text."""
        ...
