"""Turn text into vectors (lists of numbers) so similar meanings are close.

Anything with `embed_documents` and `embed_query` counts as an Embedder, so
tests can pass in a fake that needs no model download.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    """Runs a sentence-transformers model locally on the CPU. Free, no API key."""

    def __init__(self, model_name: str):
        # Imported here so code that only uses the fake never loads PyTorch.
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._model = SentenceTransformer(model_name, device="cpu")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # normalize_embeddings=True gives every vector length 1, which is what
        # cosine similarity in the vector store expects.
        vectors = self._model.encode(texts, normalize_embeddings=True, batch_size=32)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


@lru_cache
def get_embedder(model_name: str) -> SentenceTransformerEmbedder:
    """Load the model once per process; later calls reuse it.

    Loading takes a few seconds and ~500 MB of RAM, so we never want to do it
    per request.
    """
    return SentenceTransformerEmbedder(model_name)
