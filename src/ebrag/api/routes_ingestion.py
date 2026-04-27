from __future__ import annotations

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ebrag.db.session import get_session
from ebrag.extraction.llm_client import FakeLLMClient
from ebrag.extraction.single_paper_extractor import SinglePaperExtractor
from ebrag.ingestion.registry import LiteratureRegistry, PaperMetadataRow
from ebrag.parsers.base import ParserAdapter
from ebrag.parsers.grobid_parser import GrobidParser
from ebrag.parsers.jats_parser import JATSParser
from ebrag.parsers.router import ParserRouter
from ebrag.schemas.paper import PaperMetadata, SourceDocument
from ebrag.schemas.parsing import ParsedDocument

router = APIRouter(tags=["ingestion"])
SessionDep = Annotated[Session, Depends(get_session)]


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
    adapters = cast(tuple[ParserAdapter, ...], (JATSParser(), GrobidParser()))
    router_ = ParserRouter(adapters=adapters)
    return router_.parse_with_fallbacks(normalized_source)


@router.post("/extraction/{paper_id}/run")
def run_extraction(
    paper_id: str,
    payload: dict[str, Any],
    session: SessionDep,
) -> dict[str, Any]:
    llm_output = payload.get("llm_output")
    if not isinstance(llm_output, dict):
        return {"paper_id": paper_id, "error": "llm_output object is required"}
    output = SinglePaperExtractor(
        session=session,
        llm_client=FakeLLMClient({paper_id: llm_output}),
    ).run(paper_id)
    return output.model_dump()
