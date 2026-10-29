"""Retrieval-augmented generation: find relevant chunks, then let the LLM
answer using only those chunks, with citations.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from app.llm.base import LLMProvider
from app.vectorstore.chroma_store import ChromaStore, SearchResult

DEFAULT_TOP_K = 5
SNIPPET_LENGTH = 300

NOT_FOUND_EN = "I couldn't find the answer in the uploaded documents."
NOT_FOUND_TR = "Yüklenen belgelerde bu sorunun cevabını bulamadım."

SYSTEM_PROMPT = f"""You are a document assistant. Answer the user's question using ONLY the context passages provided.

Rules:
1. Use only facts stated in the context. Do not use outside knowledge and do not guess.
2. After every fact, cite its source exactly as [filename, p. N], copying the filename and page from the passage header. Cite each source in its own brackets.
3. Answer in the same language as the question (for example, a Turkish question gets a Turkish answer), even if the context is in another language. Keep the citation format [filename, p. N] in every language.
4. If the context does not contain the answer, reply with exactly one sentence and no citations:
   - for an English question: {NOT_FOUND_EN}
   - for a Turkish question: {NOT_FOUND_TR}
5. Be concise."""

# Matches citations like [invoice.pdf, p. 3]. Tolerates "s." (Turkish "sayfa").
CITATION_RE = re.compile(r"\[([^\[\]]+?),\s*(?:p|s)\.\s*(\d+)\]")
# Letters that appear in Turkish but not English.
TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")
# Common Turkish question and function words, for questions typed without
# Turkish letters (e.g. "fatura ne zaman odenmeli").
TURKISH_WORDS = {
    "ne", "nedir", "neden", "nasil", "nerede", "nereye", "hangi", "kim", "kac",
    "mi", "mu", "midir", "var", "yok", "ve", "ile", "icin", "bir", "bu", "su",
    "zaman", "gibi", "veya", "ama", "olan", "olarak",
}
LANGUAGE_NAMES = {"en": "English", "tr": "Turkish"}


class Source(BaseModel):
    doc_id: str
    filename: str
    page: int
    snippet: str
    score: float


class Answer(BaseModel):
    answer: str
    sources: list[Source]


def detect_language(text: str) -> str:
    """Return "tr" or "en". The app only supports these two languages, so a
    simple check is enough: Turkish letters, or common Turkish words.
    """
    if any(ch in TURKISH_CHARS for ch in text):
        return "tr"
    words = set(re.findall(r"[a-z]+", text.lower()))
    return "tr" if words & TURKISH_WORDS else "en"


def build_user_prompt(question: str, results: list[SearchResult]) -> str:
    passages = "\n\n".join(
        f"[Passage {i}] {r.chunk.filename}, p. {r.chunk.page}\n{r.chunk.text}"
        for i, r in enumerate(results, start=1)
    )
    # Name the language explicitly and put it last, right after the question.
    # When the context is in another language, models otherwise tend to copy
    # the context's language (found by the evaluation in eval/).
    language = LANGUAGE_NAMES[detect_language(question)]
    return (
        f"Context:\n\n{passages}\n\nQuestion: {question}\n\n"
        f"The question is in {language}. Write your entire answer in {language}, "
        f"translating facts from the context if needed."
    )


def extract_sources(answer: str, results: list[SearchResult]) -> list[Source]:
    """Turn the citations in the answer into Source objects.

    Only citations that match a retrieved chunk count, so a made-up citation
    never reaches the user. Order follows first mention in the answer.
    """
    # Best-scoring chunk for each (filename, page). Results are sorted best first.
    by_location: dict[tuple[str, int], SearchResult] = {}
    for r in results:
        by_location.setdefault((r.chunk.filename, r.chunk.page), r)

    sources: list[Source] = []
    seen: set[tuple[str, int]] = set()
    for filename, page in CITATION_RE.findall(answer):
        key = (filename.strip(), int(page))
        if key in seen or key not in by_location:
            continue
        seen.add(key)
        r = by_location[key]
        text = r.chunk.text
        snippet = text if len(text) <= SNIPPET_LENGTH else text[:SNIPPET_LENGTH].rstrip() + "…"
        sources.append(
            Source(
                doc_id=r.chunk.doc_id,
                filename=r.chunk.filename,
                page=r.chunk.page,
                snippet=snippet,
                score=round(r.score, 3),
            )
        )
    return sources


class RAGPipeline:
    def __init__(self, store: ChromaStore, llm: LLMProvider, top_k: int = DEFAULT_TOP_K):
        self._store = store
        self._llm = llm
        self._top_k = top_k

    def ask(self, question: str, doc_ids: list[str] | None = None) -> Answer:
        question = question.strip()
        if not question:
            raise ValueError("question must not be empty")

        results = self._store.search(question, top_k=self._top_k, doc_ids=doc_ids)
        if not results:
            # Nothing uploaded (or nothing in the chosen documents): don't
            # spend an LLM request on a question that can't be answered.
            message = NOT_FOUND_TR if detect_language(question) == "tr" else NOT_FOUND_EN
            return Answer(answer=message, sources=[])

        reply = self._llm.complete(SYSTEM_PROMPT, build_user_prompt(question, results))
        return Answer(answer=reply, sources=extract_sources(reply, results))
