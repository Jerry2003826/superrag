from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from ebrag.ingestion.registry import ImportSummary, LiteratureRegistry


def import_metadata_csv(session: Session, path: Path) -> ImportSummary:
    return LiteratureRegistry(session).import_csv(path)
