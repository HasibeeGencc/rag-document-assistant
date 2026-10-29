"""FastAPI app. Run locally with:  uvicorn app.main:app --reload"""

from fastapi import FastAPI

from app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Document Assistant",
        description="Upload PDFs and ask questions in English or Turkish. "
        "Answers cite the source document and page.",
        version="0.1.0",
    )
    app.include_router(router)
    return app


app = create_app()
