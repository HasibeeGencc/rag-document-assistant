# Runs the app on CPU. Also used by Hugging Face Spaces (Prompt 10).
FROM python:3.11-slim

# Python: no .pyc files, log output straight away.
# pip: no cache, so the image stays smaller.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Hugging Face Spaces runs containers as user 1000, so we do the same.
RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

# 1. CPU-only PyTorch first. Without this, sentence-transformers pulls the
#    GPU build (~2 GB extra) that a CPU server can't use.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# 2. The other dependencies. Copied before the code so Docker can reuse this
#    slow layer when only the code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# 3. Download the embedding model at build time, so the container starts
#    fast and never needs to download it at runtime.
ARG EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
ENV EMBEDDING_MODEL=${EMBEDDING_MODEL} \
    HF_HOME=/app/.cache/huggingface
RUN python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['EMBEDDING_MODEL'], device='cpu')"
# From now on, use only the downloaded copy.
ENV HF_HUB_OFFLINE=1

# 4. The app itself.
COPY app ./app
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser

# API keys are NOT baked into the image: pass them at runtime
# (docker run -e GROQ_API_KEY=... or a Space secret).
ENV CHROMA_DIR=/app/data/chroma \
    PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
