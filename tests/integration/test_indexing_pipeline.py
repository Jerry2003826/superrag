from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.db.repositories import (
    EvidenceRepository,
    PaperRepository,
    ResultRepository,
    StudyRepository,
    generate_stable_id,
)
from ebrag.indexing.build_indexes import build_indexes
from ebrag.indexing.graph_index import GraphIndexer
from ebrag.indexing.opensearch_index import FakeOpenSearchClient, OpenSearchIndexer
from ebrag.indexing.vector_index import FakeEmbeddingClient, FakeVectorClient, VectorIndexer
from ebrag.ingestion.dedup import normalize_title


def _seed_indexable_corpus(
    db_session: Session,
) -> tuple[models.Chunk, models.EvidenceSpan, models.Result]:
    paper = PaperRepository(db_session).create(
        title="Compound X indexing study",
        normalized_title=normalize_title("Compound X indexing study"),
    )
    study = StudyRepository(db_session).create()
    parsed = models.ParsedDocument(
        parsed_id=generate_stable_id(db_session, models.ParsedDocument),
        paper_id=paper.paper_id,
        source_format="JATS_XML",
        parser_name="jats",
        parser_version="0.1",
        object_uri="local://raw/doc.xml",
        parse_status="parsed",
        parse_confidence=0.95,
        qc_status="pass",
    )
    db_session.add(parsed)
    db_session.flush()
    chunk = models.Chunk(
        chunk_id=generate_stable_id(db_session, models.Chunk),
        paper_id=paper.paper_id,
        parsed_id=parsed.parsed_id,
        section="Results",
        page_start=4,
        page_end=4,
        chunk_type="body",
        text="Compound X reduced IL-6 in mice.",
        token_count=6,
        chunk_metadata={"source": "fixture"},
    )
    db_session.add(chunk)
    db_session.flush()
    span = EvidenceRepository(db_session).create_span(
        paper_id=paper.paper_id,
        study_id=study.study_id,
        chunk_id=chunk.chunk_id,
        source_format="JATS_XML",
        section="Results",
        page=4,
        text="Compound X reduced IL-6 in mice.",
    )
    result = ResultRepository(db_session).create(
        study_id=study.study_id,
        paper_id=paper.paper_id,
        evidence_span_id=span.evidence_span_id,
        study_type="animal",
        intervention="Compound X",
        outcome="IL-6",
        direction="decreased",
        scope="animal",
        extraction_status="verified",
    )
    return chunk, span, result


def test_indexing_payloads_include_traceability_fields(db_session: Session) -> None:
    chunk, span, result = _seed_indexable_corpus(db_session)
    search_client = FakeOpenSearchClient()
    vector_client = FakeVectorClient()
    build_result = build_indexes(
        chunks=[chunk],
        evidence_spans=[span],
        results=[result],
        opensearch_indexer=OpenSearchIndexer(search_client),
        vector_indexer=VectorIndexer(vector_client, FakeEmbeddingClient()),
        graph_indexer=GraphIndexer(db_session),
    )

    evidence_payload = search_client.documents["evidence_spans"][span.evidence_span_id]
    vector_payload = vector_client.points["evidence_spans"][span.evidence_span_id]["payload"]
    graph_edges = db_session.scalars(select(models.GraphEdge)).all()

    assert build_result.lexical_documents == 2
    assert build_result.vector_points == 1
    assert build_result.graph_edges == 2
    assert search_client.documents["chunks"][chunk.chunk_id]["paper_id"] == "P00000001"
    assert evidence_payload["study_id"] == "S00000001"
    assert evidence_payload["section"] == "Results"
    assert evidence_payload["page"] == 4
    assert vector_payload["paper_id"] == "P00000001"
    assert any(edge.edge_type == "SUPPORTED_BY" for edge in graph_edges)
