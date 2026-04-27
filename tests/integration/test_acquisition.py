from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from ebrag.db.repositories import BaseRepository, PaperRepository
from ebrag.ingestion.acquisition import SourceAcquisition
from ebrag.ingestion.dedup import normalize_title
from ebrag.storage.local_store import LocalStore


def test_upload_source_to_local_store(db_session: Session, tmp_path: Path) -> None:
    source = tmp_path / "paper.xml"
    source.write_text("<article />", encoding="utf-8")
    store = LocalStore(tmp_path / "objects")
    paper = PaperRepository(db_session).create(
        title="XML Paper",
        normalized_title=normalize_title("XML Paper"),
    )

    uri = SourceAcquisition(store, "raw-documents").upload_source(
        repository=BaseRepository(db_session),
        paper=paper,
        source_path=source,
    )

    assert uri.startswith("local://raw-documents/P00000001/")
    assert paper.full_text_available is True
    assert store.exists("raw-documents", uri.removeprefix("local://raw-documents/"))
