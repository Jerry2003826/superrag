from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ebrag.db import models as _models
from ebrag.db.base import Base
from ebrag.settings import load_settings

_ = _models


@pytest.fixture(autouse=True)
def isolate_runtime_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("EBRAG_PROJECT__ENVIRONMENT", "dev")
    monkeypatch.setenv("EBRAG_LLM__PROVIDER", "fake")
    monkeypatch.setenv("EBRAG_EMBEDDING__PROVIDER", "fake")
    load_settings.cache_clear()
    try:
        yield
    finally:
        load_settings.cache_clear()


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def sample_jats_path() -> Path:
    return Path(__file__).parent / "fixtures" / "sample_jats.xml"
