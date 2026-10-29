import pytest

from app.ingestion.pdf import Chunk
from app.vectorstore.chroma_store import ChromaStore
from tests.fakes import FakeEmbedder


def make_chunk(doc_id: str, filename: str, page: int, index: int, text: str) -> Chunk:
    return Chunk(
        chunk_id=f"{doc_id}:{page}:{index}",
        doc_id=doc_id,
        filename=filename,
        page=page,
        text=text,
    )


@pytest.fixture
def store(tmp_path) -> ChromaStore:
    return ChromaStore(FakeEmbedder(), persist_dir=str(tmp_path / "chroma"))


@pytest.fixture
def filled_store(store) -> ChromaStore:
    store.add_chunks(
        [
            make_chunk("d1", "invoice.pdf", 1, 0, "payment is due within thirty days"),
            make_chunk("d1", "invoice.pdf", 2, 0, "late fees are five percent per month"),
            make_chunk("d2", "fatura.pdf", 1, 0, "ödeme otuz gün içinde yapılmalıdır"),
        ]
    )
    return store


def test_empty_store_has_no_documents(store):
    assert store.list_documents() == []
    assert store.search("anything") == []


def test_search_returns_best_match_first_with_metadata(filled_store):
    results = filled_store.search("when is payment due", top_k=3)

    best = results[0]
    assert best.chunk.filename == "invoice.pdf"
    assert best.chunk.page == 1
    assert best.chunk.text == "payment is due within thirty days"
    assert [r.score for r in results] == sorted((r.score for r in results), reverse=True)


def test_search_respects_top_k(filled_store):
    assert len(filled_store.search("payment", top_k=2)) == 2


def test_search_can_filter_by_document(filled_store):
    results = filled_store.search("payment", top_k=5, doc_ids=["d2"])

    assert results and all(r.chunk.doc_id == "d2" for r in results)


def test_search_finds_turkish_text(filled_store):
    results = filled_store.search("ödeme kaç gün içinde", top_k=1)

    assert results[0].chunk.filename == "fatura.pdf"


def test_search_rejects_invalid_top_k(filled_store):
    with pytest.raises(ValueError):
        filled_store.search("payment", top_k=0)


def test_list_documents_counts_chunks(filled_store):
    docs = filled_store.list_documents()

    assert [(d.doc_id, d.filename, d.chunk_count) for d in docs] == [
        ("d2", "fatura.pdf", 1),
        ("d1", "invoice.pdf", 2),
    ]


def test_delete_document_removes_only_that_document(filled_store):
    assert filled_store.delete_document("d1") is True

    assert [d.doc_id for d in filled_store.list_documents()] == ["d2"]
    assert all(r.chunk.doc_id == "d2" for r in filled_store.search("payment due"))


def test_delete_unknown_document_returns_false(filled_store):
    assert filled_store.delete_document("missing") is False


def test_data_survives_reopening_the_store(tmp_path):
    path = str(tmp_path / "chroma")
    ChromaStore(FakeEmbedder(), persist_dir=path).add_chunks(
        [make_chunk("d1", "a.pdf", 1, 0, "persistent text")]
    )

    reopened = ChromaStore(FakeEmbedder(), persist_dir=path)

    assert [d.doc_id for d in reopened.list_documents()] == ["d1"]


def test_large_upload_is_added_in_batches(store):
    chunks = [make_chunk("big", "big.pdf", 1, i, f"chunk number {i}") for i in range(2500)]

    store.add_chunks(chunks)

    assert store.list_documents()[0].chunk_count == 2500
