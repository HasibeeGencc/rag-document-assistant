# CLAUDE.md

## Project
RAG Document Assistant: a FastAPI app where users upload PDFs and ask questions about them. Answers must cite the source document and page number. Must work for English and Turkish documents and questions; answer in the language of the question.

## Hard constraints
- Zero cost: Groq free tier for the LLM (default model `openai/gpt-oss-20b`), with a pluggable provider interface so Gemini can be swapped in via env var. Local sentence-transformers embeddings (multilingual model, e.g. `paraphrase-multilingual-MiniLM-L12-v2`). ChromaDB persisted locally.
- Secrets only in `.env` (git-ignored). Never hardcode or log API keys. Provide `.env.example`.
- Python 3.11, FastAPI, Pydantic v2, pypdf for parsing.
- Tests with pytest must run offline in CI: use fake LLM and fake embedding classes in tests.
- If the LLM can't find the answer in the retrieved chunks, it must say so rather than make something up.

## Architecture
- `app/ingestion`: PDF -> pages -> chunks with doc_id, filename, page metadata
- `app/embeddings`
- `app/vectorstore`
- `app/llm`: provider interface + groq + gemini
- `app/rag`: retrieve + prompt + answer with citations
- `app/api`: FastAPI routes
- `app/static`: simple web UI
- `tests/`
- `eval/`

## How to work with me
I'm a junior developer and want to learn. Work in small steps, explain key decisions briefly, and tell me how to run and test each step. I review and commit myself. Don't add features I didn't ask for.
