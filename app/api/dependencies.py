"""Shared objects the routes need, created once and reused.

Routes ask for these with FastAPI's Depends(). Tests replace them with fakes
through app.dependency_overrides, so no model or API key is needed.
"""

from functools import lru_cache

from fastapi import Depends, HTTPException, status

from app.config import get_settings
from app.embeddings.embedder import get_embedder
from app.llm.base import LLMProvider
from app.llm.factory import get_llm
from app.rag.pipeline import RAGPipeline
from app.vectorstore.chroma_store import ChromaStore


@lru_cache
def get_store() -> ChromaStore:
    settings = get_settings()
    return ChromaStore(get_embedder(settings.embedding_model), settings.chroma_dir)


@lru_cache
def _cached_llm() -> LLMProvider:
    return get_llm(get_settings())


def get_llm_provider() -> LLMProvider:
    try:
        return _cached_llm()
    except ValueError as exc:  # e.g. GROQ_API_KEY missing
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc


def get_pipeline(
    store: ChromaStore = Depends(get_store),
    llm: LLMProvider = Depends(get_llm_provider),
) -> RAGPipeline:
    return RAGPipeline(store, llm)
