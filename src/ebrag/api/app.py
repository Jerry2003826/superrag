from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ebrag.api.routes_eval import router as eval_router
from ebrag.api.routes_index import router as index_router
from ebrag.api.routes_ingestion import router as ingestion_router
from ebrag.api.routes_query import router as query_router
from ebrag.api.routes_review import router as review_router
from ebrag.api.security import APIKeyMiddleware, InMemoryRateLimitMiddleware
from ebrag.settings import load_settings


def create_app() -> FastAPI:
    settings = load_settings()
    application = FastAPI(
        title="Evidence Bio RAG",
        version="0.1.0",
        description="Evidence-grounded biomedical systematic review RAG engine.",
    )
    application.add_middleware(
        InMemoryRateLimitMiddleware,
        settings=settings.security,
    )
    application.add_middleware(
        APIKeyMiddleware,
        api_key=settings.security.api_key,
        header_name=settings.security.api_key_header,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origin_list,
        allow_credentials=False,
        allow_methods=settings.security.cors_method_list,
        allow_headers=settings.security.cors_header_list,
    )

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(ingestion_router)
    application.include_router(index_router)
    application.include_router(query_router)
    application.include_router(review_router)
    application.include_router(eval_router)
    return application


app = create_app()
