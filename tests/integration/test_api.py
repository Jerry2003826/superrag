from __future__ import annotations

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ebrag.api.app import create_app
from ebrag.db import models as _models
from ebrag.db.base import Base
from ebrag.db.repositories import (
    EvidenceRepository,
    PaperRepository,
    ResultRepository,
    StudyRepository,
)
from ebrag.db.session import get_session
from ebrag.ingestion.dedup import normalize_title

_ = _models


def _client_with_session() -> tuple[TestClient, Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    app = create_app()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), session


def _seed_result(session: Session) -> None:
    paper = PaperRepository(session).create(
        title="Compound X API study",
        normalized_title=normalize_title("Compound X API study"),
    )
    study = StudyRepository(session).create()
    span = EvidenceRepository(session).create_span(
        paper_id=paper.paper_id,
        study_id=study.study_id,
        source_format="JATS_XML",
        parser_name="jats",
        section="Results",
        page=4,
        text="Compound X reduced IL-6 in AD mouse models.",
    )
    ResultRepository(session).create(
        study_id=study.study_id,
        paper_id=paper.paper_id,
        evidence_span_id=span.evidence_span_id,
        study_type="animal",
        population_or_model="AD mouse model",
        species="mouse",
        intervention="Compound X",
        outcome="IL-6",
        direction="decreased",
        scope="animal",
        extraction_status="verified",
    )


def test_api_register_parse_review_eval_and_full_query() -> None:
    client, session = _client_with_session()
    register_response = client.post(
        "/papers/register",
        json={
            "title": "Compound X API paper",
            "authors": ["Smith"],
            "year": 2024,
        },
    )
    assert register_response.status_code == 200
    assert register_response.json()["paper_id"] == "P00000001"

    parse_response = client.post(
        "/papers/P00000001/parse",
        json={
            "document_id": "doc-1",
            "paper_id": "P00000001",
            "source_format": "JATS_XML",
            "uri": "memory://sample.xml",
            "filename": "sample.xml",
            "content_bytes": (
                "<article><front><article-meta><title-group>"
                "<article-title>API JATS</article-title></title-group>"
                "<abstract><p>Abstract text.</p></abstract></article-meta></front>"
                "<body><sec><title>Results</title><p>Result text.</p></sec></body></article>"
            ),
        },
    )
    assert parse_response.status_code == 200
    assert parse_response.json()["parse_status"] == "parsed"

    _seed_result(session)
    full_response = client.post(
        "/query/full",
        json={"query": "Does compound X reduce IL-6 in animal studies?", "query_scope": "animal"},
    )
    assert full_response.status_code == 200
    full_payload = full_response.json()
    assert full_payload["abstained"] is False
    assert full_payload["sufficiency"] == "sufficient"

    review_response = client.get("/review/queue")
    assert review_response.status_code == 200

    eval_response = client.post(
        "/eval/run-gold",
        json={
            "gold_cases": [
                {
                    "case_id": "case-1",
                    "query": "Does compound X reduce IL-6?",
                    "expected_result_ids": ["R00000001"],
                    "expected_evidence_span_ids": ["E00000001"],
                }
            ],
            "predictions": [
                {
                    "case_id": "case-1",
                    "retrieved_result_ids": ["R00000001"],
                    "retrieved_evidence_span_ids": ["E00000001"],
                    "claim_verdicts": ["supported"],
                    "final_claim_verdicts": ["supported"],
                }
            ],
        },
    )
    assert eval_response.status_code == 200
    assert eval_response.json()["metrics"]["release_gate_passed"] is True
