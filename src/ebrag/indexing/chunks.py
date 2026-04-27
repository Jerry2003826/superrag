from __future__ import annotations

from typing import Any

from ebrag.db import models


def chunk_payload(chunk: models.Chunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "paper_id": chunk.paper_id,
        "parsed_id": chunk.parsed_id,
        "section": chunk.section,
        "page": chunk.page_start,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "chunk_type": chunk.chunk_type,
        "text": chunk.text,
        "metadata": chunk.chunk_metadata,
    }


def evidence_span_payload(span: models.EvidenceSpan) -> dict[str, Any]:
    return {
        "evidence_span_id": span.evidence_span_id,
        "paper_id": span.paper_id,
        "study_id": span.study_id,
        "chunk_id": span.chunk_id,
        "source_format": span.source_format,
        "parser_name": span.parser_name,
        "section": span.section,
        "page": span.page,
        "scope": None,
        "text": span.text,
        "verification_status": span.verification_status,
        "source_hash": span.source_hash,
    }


def result_payload(result: models.Result) -> dict[str, Any]:
    span = result.evidence_span
    return {
        "result_id": result.result_id,
        "paper_id": result.paper_id,
        "study_id": result.study_id,
        "evidence_span_id": result.evidence_span_id,
        "section": span.section if span is not None else None,
        "page": span.page if span is not None else None,
        "scope": result.scope,
        "outcome": result.outcome,
        "intervention": result.intervention,
        "direction": result.direction,
        "text": span.text if span is not None else "",
    }
