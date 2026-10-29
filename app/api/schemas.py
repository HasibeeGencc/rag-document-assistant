"""Request and response bodies for the HTTP API.

FastAPI uses these to validate input and to generate the /docs page.
"""

from pydantic import BaseModel, Field

# These are already Pydantic models, so the API can return them directly.
from app.rag.pipeline import Answer, Source  # noqa: F401
from app.vectorstore.chroma_store import DocumentInfo  # noqa: F401


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    page_count: int
    chunk_count: int
    empty_pages: list[int] = Field(
        description="Pages with no extractable text, e.g. scanned images"
    )


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000, examples=["When is payment due?"])
    doc_ids: list[str] | None = Field(
        default=None, description="Only search these documents. Omit to search all."
    )


class HealthResponse(BaseModel):
    status: str
