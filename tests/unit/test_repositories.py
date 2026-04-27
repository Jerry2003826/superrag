from __future__ import annotations

from sqlalchemy.orm import Session

from ebrag.db.repositories import (
    ClaimRepository,
    EvidenceRepository,
    PaperRepository,
    ResultRepository,
    StudyReportRepository,
    StudyRepository,
)
from ebrag.ingestion.dedup import normalize_title


def test_create_core_evidence_chain(db_session: Session) -> None:
    papers = PaperRepository(db_session)
    studies = StudyRepository(db_session)
    reports = StudyReportRepository(db_session)
    evidence = EvidenceRepository(db_session)
    results = ResultRepository(db_session)
    claims = ClaimRepository(db_session)

    paper = papers.create(
        title="Mouse AD Study",
        normalized_title=normalize_title("Mouse AD Study"),
    )
    study = studies.create()
    report = reports.create(
        study_id=study.study_id,
        paper_id=paper.paper_id,
        report_type="primary",
        confidence=1.0,
        evidence="registry import",
    )
    span = evidence.create_span(
        paper_id=paper.paper_id,
        study_id=study.study_id,
        text="Compound X reduced IL-6 in AD mouse models.",
    )
    result = results.create(
        study_id=study.study_id,
        paper_id=paper.paper_id,
        evidence_span_id=span.evidence_span_id,
        study_type="animal",
        outcome="IL-6",
        scope="animal",
    )
    claim = claims.create_claim(answer_id="answer-1", claim_text="Compound X reduced IL-6.")
    verification = claims.create_verification(
        claim_id=claim.claim_id,
        verdict="supported",
        verifier_type="deterministic",
    )

    assert report.report_id == "REP00000001"
    assert span.evidence_span_id == "E00000001"
    assert result.result_id == "R00000001"
    assert verification.verification_id == "CV00000001"
