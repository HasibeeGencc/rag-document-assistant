"""Measure how often retrieval finds the right page, and save example answers.

    python eval/run_eval.py                 # retrieval only, no API key needed
    python eval/run_eval.py --answers       # also ask the LLM a few questions

Uses the real embedding model and a temporary vector store, so your own
uploaded documents in data/ are not touched. Results go to eval/results.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.embeddings.embedder import get_embedder  # noqa: E402
from app.ingestion.pdf import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, ingest_pdf  # noqa: E402
from app.rag.pipeline import DEFAULT_TOP_K, RAGPipeline, detect_language  # noqa: E402
from app.vectorstore.chroma_store import ChromaStore  # noqa: E402

EVAL_DIR = Path(__file__).parent
DOCS_DIR = EVAL_DIR / "docs"
K_VALUES = (1, 3, 5)
# Questions whose answers are shown in results.md. The last one is not in any
# document, to check that the assistant admits it doesn't know.
EXAMPLE_QUESTIONS = [
    "How many days a week can I work from home?",
    "Fatura kaç gün içinde ödenmeli ve gecikme faizi nedir?",
    "Yılda kaç gün ücretli izin hakkım var?",
    "How long is customer data kept after the contract ends?",
    "What uptime does the service provider guarantee?",
    "Hoparlör kaç saat çalışır?",
    "What is the name of Acme's CEO?",
]


def rank_of_answer(results, doc: str, page: int) -> int | None:
    """1-based position of the first chunk from the expected page, or None."""
    for position, r in enumerate(results, start=1):
        if r.chunk.filename == doc and r.chunk.page == page:
            return position
    return None


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    summary = {"n": n}
    for k in K_VALUES:
        summary[f"hit@{k}"] = sum(1 for r in rows if r["rank"] and r["rank"] <= k) / n
    # Mean reciprocal rank: 1 if the right page is first, 1/2 if second, ... 0 if missing.
    summary["mrr"] = sum(1 / r["rank"] for r in rows if r["rank"]) / n
    return summary


def pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval quality.")
    parser.add_argument("--answers", action="store_true", help="also generate example answers")
    args = parser.parse_args()

    settings = get_settings()
    questions = json.loads((EVAL_DIR / "questions.json").read_text(encoding="utf-8"))
    pdfs = sorted(DOCS_DIR.glob("*.pdf"))

    print(f"Loading embedding model {settings.embedding_model} ...")
    embedder = get_embedder(settings.embedding_model)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        store = ChromaStore(embedder, persist_dir=tmp)
        corpus = []
        for pdf in pdfs:
            result = ingest_pdf(pdf.read_bytes(), pdf.name, doc_id=pdf.stem)
            store.add_chunks(result.chunks)
            corpus.append((pdf.name, result.page_count, len(result.chunks)))

        rows = []
        for q in questions:
            results = store.search(q["question"], top_k=max(K_VALUES))
            rank = rank_of_answer(results, q["doc"], q["page"])
            rows.append({**q, "rank": rank, "top": results[0]})
            print(f"  [{'hit ' if rank else 'MISS'}] rank={rank} {q['question']}")

        examples = []
        if args.answers:
            from app.llm.factory import get_llm

            pipeline = RAGPipeline(store, get_llm(settings))
            for question in EXAMPLE_QUESTIONS:
                print(f"  asking: {question}")
                examples.append((question, pipeline.ask(question)))

    overall = summarise(rows)
    same = summarise([r for r in rows if not r.get("cross_lingual")])
    cross = summarise([r for r in rows if r.get("cross_lingual")])
    by_lang = {lang: summarise([r for r in rows if r["lang"] == lang]) for lang in ("en", "tr")}

    lines = [
        "# Evaluation results",
        "",
        f"Generated {dt.date.today().isoformat()} by `python eval/run_eval.py"
        f"{' --answers' if args.answers else ''}`.",
        "",
        "## Setup",
        "",
        f"- Embedding model: `{settings.embedding_model}`",
        f"- Chunk size {DEFAULT_CHUNK_SIZE} characters, overlap {DEFAULT_CHUNK_OVERLAP}; "
        f"the app sends the top {DEFAULT_TOP_K} chunks to the LLM",
        f"- {len(questions)} questions with a known answer page, over {len(pdfs)} fictional "
        f"sample documents ({sum(c[2] for c in corpus)} chunks in total):",
        "",
        "| Document | Language | Pages | Chunks |",
        "|---|---|---|---|",
    ]
    for name, pages, chunks in corpus:
        language = "Turkish" if name.startswith("nova") else "English"
        lines.append(f"| {name} | {language} | {pages} | {chunks} |")

    lines += [
        "",
        "## Retrieval: is the correct page in the top-k chunks?",
        "",
        "| Question set | n | Hit@1 | Hit@3 | Hit@5 | MRR |",
        "|---|---|---|---|---|---|",
    ]
    for label, s in [
        ("**All questions**", overall),
        ("Same language as document", same),
        ("Cross-language (TR question, EN doc or vice versa)", cross),
        ("English questions", by_lang["en"]),
        ("Turkish questions", by_lang["tr"]),
    ]:
        lines.append(
            f"| {label} | {s['n']} | {pct(s['hit@1'])} | {pct(s['hit@3'])} | "
            f"{pct(s['hit@5'])} | {s['mrr']:.2f} |"
        )

    lines += [
        "",
        "## Per question",
        "",
        "| # | Question | Expected | Rank | Top result |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        top = f"{r['top'].chunk.filename} p. {r['top'].chunk.page} ({r['top'].score:.2f})"
        rank = str(r["rank"]) if r["rank"] else "**miss**"
        tag = " (cross)" if r.get("cross_lingual") else ""
        lines.append(
            f"| {r['id']} | {r['question']}{tag} | {r['doc']} p. {r['page']} | {rank} | {top} |"
        )

    if examples:
        same_language = sum(
            detect_language(a.answer) == detect_language(q) for q, a in examples
        )
        lines += [
            "", "## Example answers", "",
            f"LLM: `{settings.llm_provider}` (`{settings.groq_model}`). "
            f"Answered in the question's language: {same_language}/{len(examples)}.", "",
        ]
        for question, answer in examples:
            sources = ", ".join(f"{s.filename} p. {s.page}" for s in answer.sources) or "none"
            lines += [f"**Q:** {question}", "", f"**A:** {answer.answer}", "",
                      f"*Sources:* {sources}", ""]

    lines += [
        "",
        "## How to read these numbers",
        "",
        "- **Hit@k** is the share of questions where a chunk from the correct page is among "
        "the k most similar chunks. Hit@5 matters most here, because the app gives the LLM "
        "5 chunks: if the right page is in them, the LLM can answer.",
        "- **MRR** (mean reciprocal rank) also rewards ranking the right page higher: "
        "1.0 means always first.",
        "- This is a small test set (26 questions, 22 chunks). With so few chunks, picking 5 "
        "at random would already find the right page about 23-41% of the time (pages have "
        "1-2 chunks), so treat these as a sanity check, not a benchmark. One question "
        "changes a score by about 4 points.",
        "- It measures **retrieval only**. Whether the final answer is correct is shown in "
        "the example answers, but not scored.",
        "",
    ]
    out = EVAL_DIR / "results.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nHit@1 {pct(overall['hit@1'])}  Hit@3 {pct(overall['hit@3'])}  "
          f"Hit@5 {pct(overall['hit@5'])}  MRR {overall['mrr']:.2f}")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
