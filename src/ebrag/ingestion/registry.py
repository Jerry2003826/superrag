from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.db.repositories import PaperRepository, StudyReportRepository, StudyRepository
from ebrag.ingestion.dedup import normalize_doi, normalize_title


@dataclass(frozen=True)
class PaperMetadataRow:
    title: str
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    abstract: str | None = None
    source_database: str | None = None
    source_url: str | None = None

    @property
    def first_author(self) -> str | None:
        return self.authors[0] if self.authors else None


@dataclass(frozen=True)
class RegisteredPaper:
    paper: models.Paper
    study: models.Study
    report: models.StudyReport
    duplicate_kind: str | None = None


@dataclass(frozen=True)
class ImportSummary:
    created: int = 0
    duplicate_papers: int = 0
    duplicate_candidates: int = 0
    registered: tuple[RegisteredPaper, ...] = ()


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _parse_authors(value: str | None) -> list[str]:
    cleaned = _clean(value)
    if cleaned is None:
        return []
    separator = ";" if ";" in cleaned else "|"
    return [author.strip() for author in cleaned.split(separator) if author.strip()]


def _parse_year(value: str | None) -> int | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    return int(cleaned)


class LiteratureRegistry:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.papers = PaperRepository(session)
        self.studies = StudyRepository(session)
        self.reports = StudyReportRepository(session)

    def register(self, metadata: PaperMetadataRow) -> RegisteredPaper:
        normalized_title = normalize_title(metadata.title)
        normalized_doi = normalize_doi(metadata.doi)

        if normalized_doi is not None:
            duplicate = self.papers.get_by_doi(normalized_doi)
            if duplicate is not None:
                self.papers.create_audit_log(
                    action="paper.duplicate_exact",
                    target_type="paper",
                    target_id=duplicate.paper_id,
                    after={"doi": normalized_doi},
                )
                report = duplicate.reports[0]
                return RegisteredPaper(
                    paper=duplicate,
                    study=report.study,
                    report=report,
                    duplicate_kind="doi",
                )

        candidate = self.papers.get_duplicate_candidate(
            normalized_title=normalized_title,
            first_author=metadata.first_author,
            year=metadata.year,
        )
        study = candidate.reports[0].study if candidate is not None and candidate.reports else None
        if study is None:
            study = self.studies.create(status="candidate")

        paper = self.papers.create(
            title=metadata.title,
            normalized_title=normalized_title,
            doi=normalized_doi,
            pmid=metadata.pmid,
            pmcid=metadata.pmcid,
            authors=metadata.authors,
            year=metadata.year,
            journal=metadata.journal,
            abstract=metadata.abstract,
            source_database=metadata.source_database,
            source_url=metadata.source_url,
        )
        report = self.reports.create(
            study_id=study.study_id,
            paper_id=paper.paper_id,
            report_type="primary" if candidate is None else "duplicate_candidate",
            confidence=1.0 if candidate is None else 0.85,
            evidence=None if candidate is None else "normalized_title + first_author + year",
            human_review_required=candidate is not None,
        )
        duplicate_kind = "candidate" if candidate is not None else None
        if duplicate_kind is not None:
            if candidate is None:
                msg = "Expected duplicate candidate when duplicate_kind is set"
                raise RuntimeError(msg)
            self.papers.create_audit_log(
                action="paper.duplicate_candidate",
                target_type="paper",
                target_id=paper.paper_id,
                after={"candidate_of": candidate.paper_id},
            )
        return RegisteredPaper(
            paper=paper,
            study=study,
            report=report,
            duplicate_kind=duplicate_kind,
        )

    def import_csv(self, path: Path) -> ImportSummary:
        created = 0
        duplicate_papers = 0
        duplicate_candidates = 0
        registered: list[RegisteredPaper] = []

        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                metadata = PaperMetadataRow(
                    title=row["title"],
                    doi=_clean(row.get("doi")),
                    pmid=_clean(row.get("pmid")),
                    pmcid=_clean(row.get("pmcid")),
                    authors=_parse_authors(row.get("authors")),
                    year=_parse_year(row.get("year")),
                    journal=_clean(row.get("journal")),
                    abstract=_clean(row.get("abstract")),
                    source_database=_clean(row.get("source_database")),
                    source_url=_clean(row.get("source_url")),
                )
                result = self.register(metadata)
                registered.append(result)
                if result.duplicate_kind == "doi":
                    duplicate_papers += 1
                elif result.duplicate_kind == "candidate":
                    duplicate_candidates += 1
                    created += 1
                else:
                    created += 1

        return ImportSummary(
            created=created,
            duplicate_papers=duplicate_papers,
            duplicate_candidates=duplicate_candidates,
            registered=tuple(registered),
        )
