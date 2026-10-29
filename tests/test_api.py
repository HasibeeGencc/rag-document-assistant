import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_llm_provider, get_store
from app.llm.base import LLMError
from app.main import create_app
from app.rag.pipeline import NOT_FOUND_EN
from app.vectorstore.chroma_store import ChromaStore
from tests.conftest import build_pdf
from tests.fakes import FakeEmbedder, FakeLLM


class FailingLLM:
    def complete(self, system: str, user: str) -> str:
        raise LLMError("Groq request failed (RateLimitError)")


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM("Payment is due within 30 days [invoice.pdf, p. 1].")


@pytest.fixture
def client(tmp_path, llm) -> TestClient:
    app = create_app()
    store = ChromaStore(FakeEmbedder(), persist_dir=str(tmp_path / "chroma"))
    # Swap the real model and LLM for fakes: offline, instant, no API key.
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_llm_provider] = lambda: llm
    return TestClient(app)


INVOICE_PDF = build_pdf(
    ["Payment is due within 30 days of delivery.", "Late fees are 5 percent per month."]
)


def upload(client, content=INVOICE_PDF, filename="invoice.pdf", mime="application/pdf"):
    return client.post("/documents", files={"file": (filename, content, mime)})


# --- health ---------------------------------------------------------------


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- upload ---------------------------------------------------------------


def test_upload_pdf(client):
    response = upload(client)

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "invoice.pdf"
    assert body["page_count"] == 2
    assert body["chunk_count"] == 2
    assert body["empty_pages"] == []
    assert body["doc_id"]


def test_upload_strips_directory_from_filename(client):
    response = upload(client, filename="../../secret/invoice.pdf")

    assert response.json()["filename"] == "invoice.pdf"


def test_upload_rejects_non_pdf_extension(client):
    response = upload(client, content=b"hello", filename="notes.txt", mime="text/plain")

    assert response.status_code == 415


def test_upload_rejects_fake_pdf(client):
    response = upload(client, content=b"not really a pdf", filename="fake.pdf")

    assert response.status_code == 415


def test_upload_rejects_empty_file(client):
    assert upload(client, content=b"").status_code == 400


def test_upload_rejects_too_large_file(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)

    assert upload(client).status_code == 413


def test_upload_rejects_corrupt_pdf(client):
    assert upload(client, content=b"%PDF-1.4 but then garbage").status_code == 422


def test_upload_rejects_pdf_without_text(client):
    response = upload(client, content=build_pdf(["", ""]), filename="scan.pdf")

    assert response.status_code == 422
    assert "No text" in response.json()["detail"]


def test_upload_without_file_is_rejected(client):
    assert client.post("/documents").status_code == 422


# --- list and delete --------------------------------------------------------


def test_list_documents(client):
    assert client.get("/documents").json() == []
    doc_id = upload(client).json()["doc_id"]

    docs = client.get("/documents").json()

    assert docs == [{"doc_id": doc_id, "filename": "invoice.pdf", "chunk_count": 2}]


def test_delete_document(client):
    doc_id = upload(client).json()["doc_id"]

    response = client.delete(f"/documents/{doc_id}")

    assert response.status_code == 204
    assert client.get("/documents").json() == []


def test_delete_unknown_document_returns_404(client):
    assert client.delete("/documents/does-not-exist").status_code == 404


# --- ask ------------------------------------------------------------------


def test_ask_returns_answer_and_sources(client, llm):
    upload(client)

    response = client.post("/ask", json={"question": "When is payment due?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == llm.reply
    assert len(body["sources"]) == 1
    source = body["sources"][0]
    assert (source["filename"], source["page"]) == ("invoice.pdf", 1)
    assert "30 days" in source["snippet"]


def test_ask_with_no_documents_says_not_found(client):
    response = client.post("/ask", json={"question": "When is payment due?"})

    assert response.json() == {"answer": NOT_FOUND_EN, "sources": []}


def test_ask_can_be_limited_to_documents(client, llm):
    upload(client)
    other_id = upload(client, content=build_pdf(["Office hours are 9 to 5."]),
                      filename="hours.pdf").json()["doc_id"]

    client.post("/ask", json={"question": "When?", "doc_ids": [other_id]})

    prompt = llm.calls[0][1]
    assert "hours.pdf" in prompt and "invoice.pdf" not in prompt


@pytest.mark.parametrize("body", [{}, {"question": ""}, {"question": "x" * 2001}])
def test_ask_validates_question(client, body):
    assert client.post("/ask", json=body).status_code == 422


def test_ask_rejects_blank_question(client):
    upload(client)

    assert client.post("/ask", json={"question": "   "}).status_code == 422


def test_ask_returns_502_when_llm_fails(client):
    client.app.dependency_overrides[get_llm_provider] = lambda: FailingLLM()
    upload(client)

    response = client.post("/ask", json={"question": "When is payment due?"})

    assert response.status_code == 502
    assert "RateLimitError" not in response.json()["detail"]


def test_ask_returns_503_when_api_key_missing(client, monkeypatch):
    from app.api import dependencies

    def missing_key():
        raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")

    del client.app.dependency_overrides[get_llm_provider]
    monkeypatch.setattr(dependencies, "_cached_llm", missing_key)

    response = client.post("/ask", json={"question": "When is payment due?"})

    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]
