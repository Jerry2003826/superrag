from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.db.session import get_session
from ebrag.extraction.llm_client import FakeLLMClient
from ebrag.extraction.single_paper_extractor import (
    ExtractionReferenceError,
    SinglePaperExtractor,
)
from ebrag.indexing.build_indexes import build_indexes
from ebrag.ingestion.documents import persist_parsed_document
from ebrag.ingestion.registry import LiteratureRegistry, PaperMetadataRow
from ebrag.parsers.base import ParserAdapter
from ebrag.parsers.grobid_parser import GrobidParser
from ebrag.parsers.jats_parser import JATSParser
from ebrag.parsers.router import ParserRouter
from ebrag.parsers.text_parser import TextParser
from ebrag.providers import build_extraction_client, build_indexers, build_object_store
from ebrag.schemas.evidence import SourceFormat
from ebrag.schemas.paper import PaperMetadata, SourceDocument
from ebrag.schemas.parsing import ParsedDocument
from ebrag.settings import load_settings
from ebrag.storage.object_store import ObjectStore

router = APIRouter(tags=["ingestion"])
SessionDep = Annotated[Session, Depends(get_session)]
ObjectStoreDep = Annotated[ObjectStore, Depends(build_object_store)]


@router.post("/papers/register")
def register_paper(
    metadata: PaperMetadata,
    session: SessionDep,
) -> dict[str, str | None]:
    row = PaperMetadataRow(
        title=metadata.title,
        doi=metadata.doi,
        pmid=metadata.pmid,
        pmcid=metadata.pmcid,
        authors=metadata.authors,
        year=metadata.year,
        journal=metadata.journal,
        abstract=metadata.abstract,
        source_database=metadata.source_database,
        source_url=metadata.source_url,
    )
    registered = LiteratureRegistry(session).register(row)
    return {
        "paper_id": registered.paper.paper_id,
        "study_id": registered.study.study_id,
        "report_id": registered.report.report_id,
        "duplicate_kind": registered.duplicate_kind,
    }


@router.post("/papers/{paper_id}/parse", response_model=ParsedDocument)
def parse_paper(paper_id: str, source: SourceDocument) -> ParsedDocument:
    normalized_source = source.model_copy(update={"paper_id": paper_id})
    adapters = cast(tuple[ParserAdapter, ...], (JATSParser(), TextParser(), GrobidParser()))
    router_ = ParserRouter(adapters=adapters)
    return router_.parse_with_fallbacks(normalized_source)


@router.post("/papers/{paper_id}/documents")
async def upload_document(
    paper_id: str,
    session: SessionDep,
    object_store: ObjectStoreDep,
    file: Annotated[UploadFile, File()],
    source_format: Annotated[SourceFormat, Form()],
    document_id: Annotated[str | None, Form()] = None,
) -> dict[str, str | int | list[str]]:
    data = await file.read()
    filename = file.filename or "document"
    normalized_document_id = document_id or filename
    key = f"{paper_id}/{normalized_document_id}/{filename}"
    settings = load_settings()
    object_uri = object_store.put_bytes(settings.storage.raw_bucket, key, data)
    source = SourceDocument(
        document_id=normalized_document_id,
        paper_id=paper_id,
        source_format=source_format,
        uri=object_uri,
        filename=filename,
        content_bytes=data,
    )
    parsed = parse_paper(paper_id, source)
    parsed_key = f"{paper_id}/{normalized_document_id}/parsed.json"
    parsed_object_uri = object_store.put_bytes(
        settings.storage.parsed_bucket,
        parsed_key,
        parsed.model_dump_json().encode("utf-8"),
    )
    default_study_id = session.scalar(
        select(models.StudyReport.study_id).where(models.StudyReport.paper_id == paper_id)
    )
    persisted = persist_parsed_document(
        session,
        parsed,
        default_study_id=default_study_id,
    )
    opensearch_indexer, vector_indexer, graph_indexer = build_indexers(session)
    index_result = build_indexes(
        chunks=persisted.chunks,
        evidence_spans=persisted.evidence_spans,
        results=[],
        opensearch_indexer=opensearch_indexer,
        vector_indexer=vector_indexer,
        graph_indexer=graph_indexer,
    )
    return {
        "object_uri": object_uri,
        "parsed_object_uri": parsed_object_uri,
        "parsed_id": persisted.parsed_document.parsed_id,
        "parse_status": persisted.parsed_document.parse_status,
        "chunk_count": len(persisted.chunks),
        "evidence_span_count": len(persisted.evidence_spans),
        "chunk_ids": [chunk.chunk_id for chunk in persisted.chunks],
        "evidence_span_ids": [span.evidence_span_id for span in persisted.evidence_spans],
        "lexical_documents": index_result.lexical_documents,
        "vector_points": index_result.vector_points,
    }


@router.post("/extraction/{paper_id}/run")
def run_extraction(
    paper_id: str,
    payload: dict[str, Any],
    session: SessionDep,
) -> dict[str, Any]:
    llm_output = payload.get("llm_output")
    settings = load_settings()
    if not isinstance(llm_output, dict) and settings.llm.provider == "fake":
        raise HTTPException(
            status_code=400,
            detail="llm_output object is required when EBRAG_LLM__PROVIDER=fake",
        )
    llm_client = (
        FakeLLMClient({paper_id: llm_output})
        if isinstance(llm_output, dict)
        else build_extraction_client()
    )
    try:
        output = SinglePaperExtractor(
            session=session,
            llm_client=llm_client,
        ).run(paper_id)
    except ExtractionReferenceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc
    return output.model_dump()
