from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.db.repositories import EvidenceRepository, PaperRepository, StudyRepository
from ebrag.extraction.llm_client import FakeLLMClient
from ebrag.extraction.single_paper_extractor import SinglePaperExtractor
from ebrag.ingestion.dedup import normalize_title


def _seed_paper_with_evidence(
    db_session: Session,
    *,
    title: str,
    evidence_text: str,
) -> tuple[models.Paper, models.Study, models.EvidenceSpan]:
    paper = PaperRepository(db_session).create(
        title=title,
        normalized_title=normalize_title(title),
    )
    study = StudyRepository(db_session).create()
    span = EvidenceRepository(db_session).create_span(
        paper_id=paper.paper_id,
        study_id=study.study_id,
        source_format="JATS_XML",
        section="Results",
        page=3,
        text=evidence_text,
    )
    return paper, study, span


def test_single_paper_extractor_persists_verified_results(
    db_session: Session, tmp_path: Path
) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "fake_extraction.json"
    _seed_paper_with_evidence(
        db_session,
        title="Compound X reduces IL-6",
        evidence_text="n=12 mice received 10 mg/kg Compound X; IL-6 decreased, p=0.01.",
    )

    output = SinglePaperExtractor(
        session=db_session,
        llm_client=FakeLLMClient.from_json_file(fixture),
    ).run("P00000001")
    results = db_session.scalars(select(models.Result)).all()
    audits = db_session.scalars(select(models.AuditLog)).all()

    assert tmp_path.exists()
    assert output.extraction_status == "verified"
    assert output.results[0].result_id == "R00000001"
    assert results[0].extraction_status == "verified"
    assert any(audit.action == "extraction.result_persisted" for audit in audits)


def test_single_paper_extractor_marks_numeric_mismatch_human_required(
    db_session: Session,
) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "fake_extraction.json"
    _seed_paper_with_evidence(
        db_session,
        title="Compound X mismatch",
        evidence_text="n=12 mice received 10 mg/kg Compound X; IL-6 decreased, p=0.01.",
    )
    # Add a second paper so the fake fixture key P00000002 matches the generated ID.
    _seed_paper_with_evidence(
        db_session,
        title="Compound X mismatch second",
        evidence_text="n=12 mice received 10 mg/kg Compound X; IL-6 decreased, p=0.01.",
    )

    output = SinglePaperExtractor(
        session=db_session,
        llm_client=FakeLLMClient.from_json_file(fixture),
    ).run("P00000002")

    assert output.extraction_status == "human_required"
    assert output.results[0].extraction_status == "human_required"


def test_single_paper_extractor_rejects_unknown_evidence_span_before_persisting(
    db_session: Session,
) -> None:
    paper, study, _span = _seed_paper_with_evidence(
        db_session,
        title="Compound X invalid evidence reference",
        evidence_text="n=12 mice received 10 mg/kg Compound X; IL-6 decreased, p=0.01.",
    )
    llm_output = {
        "paper_id": paper.paper_id,
        "extraction_status": "unverified",
        "results": [
            {
                "result_id": "R00000001",
                "study_id": study.study_id,
                "paper_id": paper.paper_id,
                "study_type": "animal",
                "population_or_model": "APP/PS1 mouse model",
                "species": "mouse",
                "cell_line": None,
                "intervention": "Compound X",
                "comparator": "vehicle",
                "outcome": "IL-6",
                "assay": "ELISA",
                "direction": "decreased",
                "effect_size": "32%",
                "p_value": "p=0.01",
                "confidence_interval": None,
                "sample_size": "n=12",
                "dose": "10 mg/kg",
                "duration": "8 weeks",
                "unit": "pg/mL",
                "scope": "animal",
                "evidence_span_id": "E99999999",
                "extraction_status": "unverified",
            }
        ],
    }

    with pytest.raises(ValueError, match="unknown evidence_span_id=E99999999"):
        SinglePaperExtractor(
            session=db_session,
            llm_client=FakeLLMClient({paper.paper_id: llm_output}),
        ).run(paper.paper_id)

    assert db_session.scalars(select(models.Result)).all() == []
