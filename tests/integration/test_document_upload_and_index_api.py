from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ebrag.api.app import create_app
from ebrag.db import models
from ebrag.db.base import Base
from ebrag.db.repositories import (
    EvidenceRepository,
    PaperRepository,
    ResultRepository,
    StudyRepository,
)
from ebrag.db.session import get_session
from ebrag.ingestion.dedup import normalize_title
from ebrag.providers import build_object_store
from ebrag.storage.local_store import LocalStore


def _client_with_session(tmp_path: Path) -> tuple[TestClient, Session]:
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
    app.dependency_overrides[build_object_store] = lambda: LocalStore(tmp_path / "objects")
    return TestClient(app), session


def test_document_upload_stores_source_and_persists_parse_outputs(tmp_path: Path) -> None:
    client, session = _client_with_session(tmp_path)
    register_response = client.post(
        "/papers/register",
        json={"title": "Upload API paper", "authors": ["Smith"], "year": 2025},
    )
    paper_id = register_response.json()["paper_id"]
    xml_bytes = (Path(__file__).parents[1] / "fixtures" / "sample_jats.xml").read_bytes()

    response = client.post(
        f"/papers/{paper_id}/documents",
        data={"source_format": "JATS_XML", "document_id": "doc-1"},
        files={"file": ("sample.xml", xml_bytes, "application/xml")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object_uri"].startswith("local://raw-documents/")
    assert payload["parsed_object_uri"].startswith("local://parsed-documents/")
    assert payload["chunk_count"] > 0
    assert payload["evidence_span_count"] > 0
    assert session.scalar(select(models.ParsedDocument)) is not None
    assert session.scalars(select(models.Chunk)).all()
    assert session.scalars(select(models.EvidenceSpan)).all()


def test_index_rebuild_api_indexes_current_database_corpus(tmp_path: Path) -> None:
    client, session = _client_with_session(tmp_path)
    paper = PaperRepository(session).create(
        title="Index rebuild paper",
        normalized_title=normalize_title("Index rebuild paper"),
    )
    study = StudyRepository(session).create()
    span = EvidenceRepository(session).create_span(
        paper_id=paper.paper_id,
        study_id=study.study_id,
        source_format="JATS_XML",
        parser_name="jats",
        section="Results",
        text="Compound X reduced IL-6.",
    )
    ResultRepository(session).create(
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

    response = client.post("/index/rebuild", json={"paper_id": paper.paper_id})

    assert response.status_code == 200
    assert response.json()["vector_points"] == 1
    assert response.json()["graph_edges"] == 2
