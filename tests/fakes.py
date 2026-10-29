"""Test doubles that replace slow or online parts of the app."""

import hashlib
import math
import re


class FakeEmbedder:
    """Deterministic "bag of words" embedder: no model download, instant.

    Each word is hashed into one of `dim` slots, so texts that share words get
    similar vectors. That is crude, but enough to check that search returns
    the chunk with the matching words.
    """

    def __init__(self, dim: int = 64):
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for word in re.findall(r"\w+", text.lower()):
            slot = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim
            vector[slot] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
