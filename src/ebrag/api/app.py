from __future__ import annotations

from fastapi import FastAPI

from ebrag.api.routes_eval import router as eval_router
from ebrag.api.routes_ingestion import router as ingestion_router
from ebrag.api.routes_query import router as query_router
from ebrag.api.routes_review import router as review_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Evidence Bio RAG",
        version="0.1.0",
        description="Evidence-grounded biomedical systematic review RAG engine.",
    )

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(ingestion_router)
    application.include_router(query_router)
    application.include_router(review_router)
    application.include_router(eval_router)
    return application


app = create_app()
