"""FastAPI app. Run locally with:  uvicorn app.main:app --reload"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Document Assistant",
        description="Upload PDFs and ask questions in English or Turkish. "
        "Answers cite the source document and page.",
        version="0.1.0",
    )
    app.include_router(router)

    # The web UI: index.html at "/", its CSS and JS under /static.
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
