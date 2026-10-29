"""HTTP endpoints. Each route validates input, calls the core modules, and
turns their errors into the right HTTP status code.
"""

from pathlib import PurePath

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from app.api.dependencies import get_pipeline, get_store
from app.api.schemas import Answer, AskRequest, DocumentInfo, HealthResponse, UploadResponse
from app.config import get_settings
from app.ingestion.pdf import PDFParseError, ingest_pdf
from app.llm.base import LLMError
from app.rag.pipeline import RAGPipeline
from app.vectorstore.chroma_store import ChromaStore

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post(
    "/documents",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
def upload_document(
    file: UploadFile = File(..., description="A PDF file"),
    store: ChromaStore = Depends(get_store),
) -> UploadResponse:
    # Keep only the name: a client could send "../../something.pdf".
    filename = PurePath(file.filename or "").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF files are accepted")

    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)  # read one byte extra to detect "too big"
    if len(data) > max_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"File is larger than {get_settings().max_upload_mb} MB",
        )
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is empty")
    # Every real PDF starts with these bytes; the extension alone can lie.
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File is not a valid PDF")

    try:
        result = ingest_pdf(data, filename)
    except PDFParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    if not result.chunks:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "No text found in this PDF. Scanned documents need OCR, which is not supported.",
        )

    store.add_chunks(result.chunks)
    return UploadResponse(
        doc_id=result.doc_id,
        filename=result.filename,
        page_count=result.page_count,
        chunk_count=len(result.chunks),
        empty_pages=result.empty_pages,
    )


@router.get("/documents", response_model=list[DocumentInfo], tags=["documents"])
def list_documents(store: ChromaStore = Depends(get_store)) -> list[DocumentInfo]:
    return store.list_documents()


@router.delete(
    "/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["documents"]
)
def delete_document(doc_id: str, store: ChromaStore = Depends(get_store)) -> Response:
    if not store.delete_document(doc_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/ask", response_model=Answer, tags=["questions"])
def ask(request: AskRequest, pipeline: RAGPipeline = Depends(get_pipeline)) -> Answer:
    try:
        return pipeline.ask(request.question, doc_ids=request.doc_ids)
    except ValueError as exc:  # e.g. a question that is only spaces
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except LLMError as exc:
        # 502 = we are fine, but the service we depend on failed.
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "The language model is unavailable. Try again shortly."
        ) from exc
