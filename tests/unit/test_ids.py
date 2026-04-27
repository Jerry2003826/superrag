from __future__ import annotations

from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.db.repositories import PaperRepository, generate_stable_id
from ebrag.ingestion.dedup import normalize_title


def test_stable_ids_increment_by_table(db_session: Session) -> None:
    papers = PaperRepository(db_session)
    first = papers.create(title="A Study", normalized_title=normalize_title("A Study"))
    second = papers.create(title="B Study", normalized_title=normalize_title("B Study"))

    assert first.paper_id == "P00000001"
    assert second.paper_id == "P00000002"
    assert generate_stable_id(db_session, models.Study) == "S00000001"


def test_normalize_title_removes_punctuation_and_spaces() -> None:
    assert normalize_title("  IL-6, Reduction: A  Study! ") == "il6 reduction a study"
