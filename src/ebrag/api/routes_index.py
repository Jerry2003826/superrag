from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.db.session import get_session
from ebrag.indexing.build_indexes import build_indexes
from ebrag.providers import build_indexers

router = APIRouter(prefix="/index", tags=["index"])
SessionDep = Annotated[Session, Depends(get_session)]


class IndexRebuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str | None = None


@router.post("/rebuild")
def rebuild_index(request: IndexRebuildRequest, session: SessionDep) -> dict[str, int]:
    chunk_query = select(models.Chunk)
    span_query = select(models.EvidenceSpan)
    result_query = select(models.Result)
    if request.paper_id is not None:
        chunk_query = chunk_query.where(models.Chunk.paper_id == request.paper_id)
        span_query = span_query.where(models.EvidenceSpan.paper_id == request.paper_id)
        result_query = result_query.where(models.Result.paper_id == request.paper_id)

    chunks = list(session.scalars(chunk_query))
    spans = list(session.scalars(span_query))
    results = list(session.scalars(result_query))
    opensearch_indexer, vector_indexer, graph_indexer = build_indexers(session)
    result = build_indexes(
        chunks=chunks,
        evidence_spans=spans,
        results=results,
        opensearch_indexer=opensearch_indexer,
        vector_indexer=vector_indexer,
        graph_indexer=graph_indexer,
    )
    return {
        "lexical_documents": result.lexical_documents,
        "vector_points": result.vector_points,
        "graph_edges": result.graph_edges,
    }
