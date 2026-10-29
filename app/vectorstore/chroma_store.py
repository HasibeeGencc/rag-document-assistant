"""Store chunk vectors in ChromaDB and search them by meaning.

ChromaDB saves everything to a folder on disk (data/chroma by default), so
uploaded documents survive an app restart.
"""

from __future__ import annotations

import chromadb
from pydantic import BaseModel

from app.embeddings.embedder import Embedder
from app.ingestion.pdf import Chunk

COLLECTION_NAME = "documents"
# Chroma rejects batches above ~5,400 items; stay well under that.
ADD_BATCH_SIZE = 1000


class SearchResult(BaseModel):
    chunk: Chunk
    score: float  # cosine similarity: 1.0 = same meaning, ~0 = unrelated


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int


class ChromaStore:
    def __init__(self, embedder: Embedder, persist_dir: str):
        self._embedder = embedder
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            COLLECTION_NAME,
            # We compute embeddings ourselves, so Chroma must not add its own.
            embedding_function=None,
            # Cosine compares direction, not length: the usual choice for
            # sentence embeddings.
            configuration={"hnsw": {"space": "cosine"}},
        )

    def add_chunks(self, chunks: list[Chunk]) -> None:
        for start in range(0, len(chunks), ADD_BATCH_SIZE):
            batch = chunks[start : start + ADD_BATCH_SIZE]
            self._collection.add(
                ids=[c.chunk_id for c in batch],
                documents=[c.text for c in batch],
                embeddings=self._embedder.embed_documents([c.text for c in batch]),
                metadatas=[
                    {"doc_id": c.doc_id, "filename": c.filename, "page": c.page}
                    for c in batch
                ],
            )

    def search(
        self, query: str, top_k: int = 5, doc_ids: list[str] | None = None
    ) -> list[SearchResult]:
        """Return the top_k chunks most similar to the query, best first.

        If doc_ids is given, only chunks from those documents are searched.
        """
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        where = {"doc_id": {"$in": doc_ids}} if doc_ids else None
        result = self._collection.query(
            query_embeddings=[self._embedder.embed_query(query)],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        # Chroma returns one list per query embedding; we sent one.
        return [
            SearchResult(
                chunk=Chunk(
                    chunk_id=chunk_id,
                    doc_id=meta["doc_id"],
                    filename=meta["filename"],
                    page=meta["page"],
                    text=text,
                ),
                score=1.0 - distance,  # Chroma's cosine distance = 1 - similarity
            )
            for chunk_id, text, meta, distance in zip(
                result["ids"][0],
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
            )
        ]

    def list_documents(self) -> list[DocumentInfo]:
        """One entry per uploaded document, sorted by filename.

        Reads every chunk's metadata, which is fine for the few hundred
        documents a small business would upload.
        """
        docs: dict[str, DocumentInfo] = {}
        for meta in self._collection.get(include=["metadatas"])["metadatas"]:
            doc = docs.get(meta["doc_id"])
            if doc is None:
                docs[meta["doc_id"]] = DocumentInfo(
                    doc_id=meta["doc_id"], filename=meta["filename"], chunk_count=1
                )
            else:
                doc.chunk_count += 1
        return sorted(docs.values(), key=lambda d: d.filename.lower())

    def delete_document(self, doc_id: str) -> bool:
        """Delete all chunks of a document. Returns False if it didn't exist."""
        ids = self._collection.get(where={"doc_id": doc_id}, include=[])["ids"]
        if not ids:
            return False
        self._collection.delete(ids=ids)
        return True
