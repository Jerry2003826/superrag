from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ebrag.api.app import create_app
from ebrag.api.security import public_error_detail
from ebrag.db import models as _models
from ebrag.db.base import Base
from ebrag.db.session import get_session
from ebrag.providers import build_object_store
from ebrag.settings import load_settings
from ebrag.storage.local_store import LocalStore

_ = _models


def _client_with_session(tmp_path: Path | None = None) -> tuple[TestClient, Session]:
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
    if tmp_path is not None:
        app.dependency_overrides[build_object_store] = lambda: LocalStore(tmp_path / "objects")
    return TestClient(app), session


def test_api_key_required_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EBRAG_SECURITY__API_KEY", "test-secret")
    load_settings.cache_clear()
    client, _ = _client_with_session()

    assert client.get("/health").status_code == 200
    assert client.post("/query/full", json={"query": "x"}).status_code == 401
    assert (
        client.post("/query/full", headers={"X-API-Key": "wrong"}, json={"query": "x"}).status_code
        == 401
    )

    authed = client.post("/query/full", headers={"X-API-Key": "test-secret"}, json={})
    assert authed.status_code != 401


def test_cors_rejects_unconfigured_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EBRAG_SECURITY__API_KEY", "test-secret")
    load_settings.cache_clear()
    client, _ = _client_with_session()

    allowed = client.options(
        "/query/full",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"

    denied = client.options(
        "/query/full",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )
    assert "access-control-allow-origin" not in denied.headers


def test_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EBRAG_SECURITY__API_KEY", "test-secret")
    monkeypatch.setenv("EBRAG_SECURITY__RATE_LIMIT_QUERY", "1/minute")
    load_settings.cache_clear()
    client, _ = _client_with_session()

    first = client.post("/query/full", headers={"X-API-Key": "test-secret"}, json={})
    second = client.post("/query/full", headers={"X-API-Key": "test-secret"}, json={})

    assert first.status_code != 429
    assert second.status_code == 429


def test_public_error_detail_redacts_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EBRAG_PROJECT__ENVIRONMENT", "prod")
    monkeypatch.setenv("EBRAG_LLM__PROVIDER", "openai")
    monkeypatch.setenv("EBRAG_EMBEDDING__PROVIDER", "sentence_transformers")
    monkeypatch.setenv("EBRAG_SECURITY__API_KEY", "test-secret")
    load_settings.cache_clear()

    try:
        assert (
            public_error_detail("internal validation details", production_message="Invalid request")
            == "Invalid request"
        )
    finally:
        load_settings.cache_clear()


def test_upload_rejects_oversized_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("EBRAG_SECURITY__UPLOAD_MAX_BYTES", "4")
    load_settings.cache_clear()
    client, _ = _client_with_session(tmp_path)
    paper_id = client.post("/papers/register", json={"title": "Upload size test"}).json()[
        "paper_id"
    ]

    response = client.post(
        f"/papers/{paper_id}/documents",
        data={"source_format": "TEXT", "document_id": "small.txt"},
        files={"file": ("small.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 413


def test_upload_rejects_invalid_extension(tmp_path: Path) -> None:
    client, _ = _client_with_session(tmp_path)
    paper_id = client.post("/papers/register", json={"title": "Upload extension test"}).json()[
        "paper_id"
    ]

    response = client.post(
        f"/papers/{paper_id}/documents",
        data={"source_format": "TEXT", "document_id": "bad.exe"},
        files={"file": ("bad.exe", b"hello", "text/plain")},
    )

    assert response.status_code == 400


def test_upload_sanitizes_object_key(tmp_path: Path) -> None:
    client, _ = _client_with_session(tmp_path)
    paper_id = client.post("/papers/register", json={"title": "Upload safe key test"}).json()[
        "paper_id"
    ]
    xml_bytes = (Path(__file__).parents[1] / "fixtures" / "sample_jats.xml").read_bytes()

    response = client.post(
        f"/papers/{paper_id}/documents",
        data={"source_format": "JATS_XML", "document_id": "../nested/doc-1"},
        files={"file": ("../sample.xml", xml_bytes, "application/xml")},
    )

    assert response.status_code == 200
    assert ".." not in response.json()["object_uri"]
