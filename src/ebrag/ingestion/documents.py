from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.db.repositories import generate_stable_id
from ebrag.schemas.parsing import ParsedDocument


@dataclass(frozen=True)
class PersistedParsedDocument:
    parsed_document: models.ParsedDocument
    chunks: list[models.Chunk]
    evidence_spans: list[models.EvidenceSpan]


def persist_parsed_document(
    session: Session,
    parsed: ParsedDocument,
) -> PersistedParsedDocument:
    parsed_model = models.ParsedDocument(
        parsed_id=generate_stable_id(session, models.ParsedDocument),
        paper_id=parsed.paper_id,
        source_format=parsed.source_format,
        parser_name=parsed.parser_name,
        parser_version=parsed.parser_version,
        object_uri=parsed.object_uri,
        parse_status=parsed.parse_status,
        parse_confidence=parsed.parse_confidence,
        qc_status=parsed.qc_status,
    )
    session.add(parsed_model)
    session.flush()

    chunk_models: list[models.Chunk] = []
    for chunk in parsed.chunks:
        chunk_model = models.Chunk(
            chunk_id=generate_stable_id(session, models.Chunk),
            paper_id=parsed.paper_id,
            parsed_id=parsed_model.parsed_id,
            section=chunk.section,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            chunk_type=chunk.chunk_type,
            text=chunk.text,
            token_count=chunk.token_count,
            chunk_metadata=chunk.metadata,
        )
        session.add(chunk_model)
        session.flush()
        chunk_models.append(chunk_model)

    span_models: list[models.EvidenceSpan] = []
    for index, span in enumerate(parsed.evidence_candidate_spans):
        linked_chunk = chunk_models[index] if index < len(chunk_models) else None
        span_model = models.EvidenceSpan(
            evidence_span_id=generate_stable_id(session, models.EvidenceSpan),
            paper_id=parsed.paper_id,
            study_id=span.study_id,
            chunk_id=linked_chunk.chunk_id if linked_chunk is not None else None,
            source_format=span.source_format,
            parser_name=span.parser_name,
            parser_version=span.parser_version,
            section=span.section,
            page=span.page,
            paragraph=span.paragraph,
            figure_or_table=span.figure_or_table,
            table_row=span.table_row,
            table_column=span.table_column,
            bbox=span.bbox.model_dump() if span.bbox is not None else None,
            char_start=span.char_start,
            char_end=span.char_end,
            text=span.text,
            parse_confidence=span.parse_confidence,
            source_hash=span.source_hash,
        )
        session.add(span_model)
        session.flush()
        span_models.append(span_model)

    return PersistedParsedDocument(
        parsed_document=parsed_model,
        chunks=chunk_models,
        evidence_spans=span_models,
    )
