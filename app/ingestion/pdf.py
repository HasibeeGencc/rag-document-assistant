"""Turn a PDF into page-aware text chunks.

Flow: PDF bytes -> list[Page] (one per PDF page) -> list[Chunk].

Chunks never cross a page boundary, so every chunk has exactly one page
number. That keeps citations like [report.pdf, p. 3] accurate.
"""

from __future__ import annotations

import io
import logging
import re
import uuid

from pydantic import BaseModel
from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)

# The embedding model (paraphrase-multilingual-MiniLM-L12-v2) only reads the
# first 128 tokens of each text and silently ignores the rest. ~500 characters
# is roughly 100-128 tokens for English, and Turkish uses a few more tokens
# per word, so 500 keeps almost every chunk fully "visible" to the model.
DEFAULT_CHUNK_SIZE = 500
# Overlap means a sentence cut at the end of one chunk also appears at the
# start of the next, so an answer split across the cut can still be found.
DEFAULT_CHUNK_OVERLAP = 100


class PDFParseError(Exception):
    """The file could not be read as a PDF (corrupt, encrypted, not a PDF)."""


class Page(BaseModel):
    page: int  # 1-based, as humans count pages
    text: str


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    page: int
    text: str


class IngestResult(BaseModel):
    doc_id: str
    filename: str
    page_count: int
    chunks: list[Chunk]
    empty_pages: list[int]  # pages with no extractable text (e.g. scanned images)


def _clean(text: str) -> str:
    """Collapse runs of whitespace so chunk sizes reflect real content."""
    return re.sub(r"\s+", " ", text).strip()


def extract_pages(data: bytes) -> list[Page]:
    """Extract text from every page of a PDF, in order.

    Pages that have no text (blank or scanned images) are returned with
    text="" rather than dropped, so page numbers stay correct.
    """
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            # Many "encrypted" PDFs use an empty password and open fine.
            if not reader.decrypt(""):
                raise PDFParseError("PDF is password-protected")
        raw_pages = list(reader.pages)
    except PDFParseError:
        raise
    except (PdfReadError, ValueError, OSError) as exc:
        raise PDFParseError(f"Could not read PDF: {exc}") from exc

    pages = []
    for number, raw_page in enumerate(raw_pages, start=1):
        try:
            text = raw_page.extract_text() or ""
        except Exception as exc:  # one broken page shouldn't fail the whole file
            logger.warning("Could not extract text from page %d: %s", number, exc)
            text = ""
        pages.append(Page(page=number, text=_clean(text)))
    return pages


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping pieces of at most chunk_size characters.

    Cuts are moved back to the nearest sentence end or space so words are not
    broken in half.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    pieces = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # Look for a good cut point in the second half of the window.
            window = text[start + chunk_size // 2 : end]
            sentence_end = max(window.rfind(". "), window.rfind("? "), window.rfind("! "))
            if sentence_end != -1:
                end = start + chunk_size // 2 + sentence_end + 1
            else:
                space = window.rfind(" ")
                if space != -1:
                    end = start + chunk_size // 2 + space

        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break

        # Step back by `overlap`, then forward to a word start so the next
        # chunk doesn't begin mid-word.
        next_start = max(end - overlap, start + 1)
        while 0 < next_start < end and not text[next_start - 1].isspace():
            next_start += 1
        start = next_start
    return pieces


def chunk_pages(
    pages: list[Page],
    doc_id: str,
    filename: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    """Split each page into chunks that carry doc_id, filename and page."""
    chunks = []
    for page in pages:
        for index, piece in enumerate(split_text(page.text, chunk_size, overlap)):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc_id}:{page.page}:{index}",
                    doc_id=doc_id,
                    filename=filename,
                    page=page.page,
                    text=piece,
                )
            )
    return chunks


def ingest_pdf(
    data: bytes,
    filename: str,
    doc_id: str | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> IngestResult:
    """Full ingestion: PDF bytes -> chunks with metadata."""
    doc_id = doc_id or uuid.uuid4().hex
    pages = extract_pages(data)
    return IngestResult(
        doc_id=doc_id,
        filename=filename,
        page_count=len(pages),
        chunks=chunk_pages(pages, doc_id, filename, chunk_size, overlap),
        empty_pages=[p.page for p in pages if not p.text],
    )
