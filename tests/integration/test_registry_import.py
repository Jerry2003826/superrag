from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.ingestion.registry import LiteratureRegistry


def test_import_metadata_csv_deduplicates_and_links_reports(
    db_session: Session, tmp_path: Path
) -> None:
    csv_path = tmp_path / "papers.csv"
    csv_path.write_text(
        "\n".join(
            [
                "title,doi,authors,year,journal,abstract,source_database,source_url",
                "Compound X reduces IL-6,10.1000/a,Smith;Liu,2024,BioMed,Mouse study,pmc,http://one",
                "Compound X reduces IL-6,10.1000/a,Smith;Liu,2024,BioMed,Duplicate DOI,pmc,http://two",
                "Compound X reduces IL-6,10.1000/b,Smith;Patel,2024,BioMed,Duplicate candidate,pmc,http://three",
            ]
        ),
        encoding="utf-8",
    )

    summary = LiteratureRegistry(db_session).import_csv(csv_path)

    papers = db_session.scalars(select(models.Paper)).all()
    studies = db_session.scalars(select(models.Study)).all()
    reports = db_session.scalars(select(models.StudyReport)).all()
    audits = db_session.scalars(select(models.AuditLog)).all()

    assert summary.created == 2
    assert summary.duplicate_papers == 1
    assert summary.duplicate_candidates == 1
    assert len(papers) == 2
    assert len(studies) == 1
    assert len(reports) == 2
    assert {report.report_type for report in reports} == {"primary", "duplicate_candidate"}
    assert any(audit.action == "paper.duplicate_exact" for audit in audits)
    assert any(audit.action == "paper.duplicate_candidate" for audit in audits)
