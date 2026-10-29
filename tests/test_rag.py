from types import SimpleNamespace

import pytest

from app.config import Settings
from app.ingestion.pdf import Chunk
from app.llm.base import LLMError
from app.llm.factory import get_llm
from app.llm.gemini_provider import GeminiProvider
from app.llm.groq_provider import GroqProvider
from app.rag.pipeline import NOT_FOUND_EN, NOT_FOUND_TR, RAGPipeline, detect_language
from app.vectorstore.chroma_store import ChromaStore
from tests.fakes import FakeEmbedder, FakeLLM


@pytest.fixture
def store(tmp_path) -> ChromaStore:
    store = ChromaStore(FakeEmbedder(), persist_dir=str(tmp_path / "chroma"))
    store.add_chunks(
        [
            Chunk(chunk_id="d1:1:0", doc_id="d1", filename="invoice.pdf", page=1,
                  text="Payment is due within 30 days of delivery."),
            Chunk(chunk_id="d1:2:0", doc_id="d1", filename="invoice.pdf", page=2,
                  text="Late payment fees are 5 percent per month."),
            Chunk(chunk_id="d2:4:0", doc_id="d2", filename="izin.pdf", page=4,
                  text="Çalışanlar yılda 14 gün ücretli izin hakkına sahiptir."),
        ]
    )
    return store


@pytest.fixture
def empty_store(tmp_path) -> ChromaStore:
    return ChromaStore(FakeEmbedder(), persist_dir=str(tmp_path / "empty"))


# --- prompt ---------------------------------------------------------------


def test_prompt_contains_question_context_and_rules(store):
    llm = FakeLLM("Within 30 days [invoice.pdf, p. 1].")

    RAGPipeline(store, llm).ask("When is payment due?")

    system, user = llm.calls[0]
    assert "ONLY" in system and "[filename, p. N]" in system
    assert NOT_FOUND_EN in system and NOT_FOUND_TR in system
    assert "Question: When is payment due?" in user
    assert "invoice.pdf, p. 1\nPayment is due within 30 days" in user


def test_top_k_limits_passages_sent_to_llm(store):
    llm = FakeLLM()

    RAGPipeline(store, llm, top_k=2).ask("payment")

    assert llm.calls[0][1].count("[Passage") == 2


def test_doc_ids_filter_limits_context(store):
    llm = FakeLLM()

    RAGPipeline(store, llm).ask("payment", doc_ids=["d2"])

    user = llm.calls[0][1]
    assert "izin.pdf" in user and "invoice.pdf" not in user


# --- sources --------------------------------------------------------------


def test_cited_sources_are_returned_with_snippets(store):
    llm = FakeLLM(
        "Payment is due in 30 days [invoice.pdf, p. 1]; late fees are 5% [invoice.pdf, p. 2]."
    )

    answer = RAGPipeline(store, llm).ask("When is payment due and what are late fees?")

    assert answer.answer == llm.reply
    assert [(s.filename, s.page) for s in answer.sources] == [
        ("invoice.pdf", 1),
        ("invoice.pdf", 2),
    ]
    assert answer.sources[0].snippet == "Payment is due within 30 days of delivery."
    assert answer.sources[0].doc_id == "d1"


def test_repeated_citation_is_listed_once(store):
    llm = FakeLLM("30 days [invoice.pdf, p. 1]. Again: [invoice.pdf, p. 1].")

    answer = RAGPipeline(store, llm).ask("When is payment due?")

    assert len(answer.sources) == 1


def test_citation_not_in_retrieved_chunks_is_ignored(store):
    llm = FakeLLM("Made up [secret.pdf, p. 9] and real [invoice.pdf, p. 1].")

    answer = RAGPipeline(store, llm).ask("When is payment due?")

    assert [(s.filename, s.page) for s in answer.sources] == [("invoice.pdf", 1)]


def test_turkish_page_abbreviation_is_understood(store):
    llm = FakeLLM("Çalışanlar yılda 14 gün izin alır [izin.pdf, s. 4].")

    answer = RAGPipeline(store, llm).ask("Kaç gün izin var?")

    assert [(s.filename, s.page) for s in answer.sources] == [("izin.pdf", 4)]


def test_not_found_answer_has_no_sources(store):
    llm = FakeLLM(NOT_FOUND_EN)

    answer = RAGPipeline(store, llm).ask("Who is the CEO?")

    assert answer.answer == NOT_FOUND_EN
    assert answer.sources == []


# --- nothing to search ------------------------------------------------------


def test_empty_store_says_not_found_without_calling_llm(empty_store):
    llm = FakeLLM()

    answer = RAGPipeline(empty_store, llm).ask("When is payment due?")

    assert answer.answer == NOT_FOUND_EN
    assert llm.calls == []


def test_empty_store_answers_turkish_question_in_turkish(empty_store):
    answer = RAGPipeline(empty_store, FakeLLM()).ask("Ödeme ne zaman yapılmalı?")

    assert answer.answer == NOT_FOUND_TR


def test_empty_question_is_rejected(store):
    with pytest.raises(ValueError):
        RAGPipeline(store, FakeLLM()).ask("   ")


@pytest.mark.parametrize(
    "question, language",
    [
        ("Şirket nerede?", "tr"),
        ("fatura ne zaman odenmeli", "tr"),  # Turkish typed without Turkish letters
        ("Where is the company?", "en"),
        ("How long is customer data kept?", "en"),
    ],
)
def test_detect_language(question, language):
    assert detect_language(question) == language


@pytest.mark.parametrize(
    "question, language",
    [("How long is data kept?", "English"), ("Veriler ne kadar saklanır?", "Turkish")],
)
def test_prompt_names_the_answer_language(store, question, language):
    llm = FakeLLM()

    RAGPipeline(store, llm).ask(question)

    assert f"Write your entire answer in {language}" in llm.calls[0][1]


# --- providers ------------------------------------------------------------


def fake_groq_client(reply="hi", error=None):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if error:
            raise error
        message = SimpleNamespace(content=reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    return client, calls


def test_groq_provider_sends_system_and_user_messages():
    client, calls = fake_groq_client(reply="  answer  ")

    reply = GroqProvider("key", "openai/gpt-oss-20b", client=client).complete("sys", "usr")

    assert reply == "answer"
    assert calls[0]["model"] == "openai/gpt-oss-20b"
    assert calls[0]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "usr"},
    ]


def test_groq_provider_wraps_errors_without_leaking_details():
    client, _ = fake_groq_client(error=RuntimeError("key gsk_secret rejected"))

    with pytest.raises(LLMError) as info:
        GroqProvider("key", "m", client=client).complete("sys", "usr")

    assert "gsk_secret" not in str(info.value)


def test_gemini_provider_returns_text():
    calls = []

    def generate_content(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text="gemini answer")

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))

    reply = GeminiProvider("key", "gemini-2.5-flash", client=client).complete("sys", "usr")

    assert reply == "gemini answer"
    assert calls[0]["contents"] == "usr"
    assert calls[0]["config"].system_instruction == "sys"


# --- factory --------------------------------------------------------------


def make_settings(**values) -> Settings:
    return Settings(_env_file=None, **values)  # ignore the real .env in tests


def test_factory_picks_groq_by_default():
    assert isinstance(get_llm(make_settings(groq_api_key="test")), GroqProvider)


def test_factory_picks_gemini_when_configured():
    llm = get_llm(make_settings(llm_provider="gemini", gemini_api_key="test"))

    assert isinstance(llm, GeminiProvider)


@pytest.mark.parametrize("key", [None, "", "   "])
def test_factory_requires_api_key(key):
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        get_llm(make_settings(groq_api_key=key))


def test_api_key_is_hidden_when_settings_are_printed():
    settings = make_settings(groq_api_key="gsk_very_secret")

    assert "gsk_very_secret" not in repr(settings)
