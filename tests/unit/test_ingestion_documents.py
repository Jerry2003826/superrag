from __future__ import annotations

from sqlalchemy.orm import Session

from ebrag.db.repositories import PaperRepository, StudyRepository
from ebrag.ingestion.dedup import normalize_title
from ebrag.ingestion.documents import persist_parsed_document
from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.parsing import ParsedChunk, ParsedDocument


def test_persist_parsed_document_applies_default_study_id(
    db_session: Session,
) -> None:
    paper = PaperRepository(db_session).create(
        title="Compound X parsed paper",
        normalized_title=normalize_title("Compound X parsed paper"),
    )
    study = StudyRepository(db_session).create()
    parsed = ParsedDocument(
        parsed_id="PD00000001",
        paper_id=paper.paper_id,
        source_format="JATS_XML",
        parser_name="jats",
        object_uri="minio://parsed-documents/sample/parsed.json",
        parse_status="parsed",
        chunks=[
            ParsedChunk(
                chunk_id="C00000001",
                paper_id=paper.paper_id,
                chunk_type="body",
                section="Results",
                text="Compound X reduced IL-6 by 32%.",
                source_format="JATS_XML",
            )
        ],
        evidence_candidate_spans=[
            EvidenceSpan(
                evidence_span_id="E00000001",
                paper_id=paper.paper_id,
                source_format="JATS_XML",
                parser_name="jats",
                section="Results",
                text="Compound X reduced IL-6 by 32%.",
            )
        ],
    )

    persisted = persist_parsed_document(
        db_session,
        parsed,
        default_study_id=study.study_id,
    )

    assert persisted.evidence_spans[0].study_id == study.study_id

