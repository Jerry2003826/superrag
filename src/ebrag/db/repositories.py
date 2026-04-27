from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models

ModelT = TypeVar("ModelT", bound=object)


@dataclass(frozen=True)
class IdSpec:
    prefix: str
    width: int = 8


ID_SPECS: dict[type[object], IdSpec] = {
    models.Paper: IdSpec("P"),
    models.Study: IdSpec("S"),
    models.StudyReport: IdSpec("REP"),
    models.ParsedDocument: IdSpec("PD"),
    models.Chunk: IdSpec("C"),
    models.EvidenceSpan: IdSpec("E"),
    models.ScreeningDecision: IdSpec("D"),
    models.Result: IdSpec("R"),
    models.GraphNode: IdSpec("GN"),
    models.GraphEdge: IdSpec("GE"),
    models.Claim: IdSpec("CLM"),
    models.ClaimVerification: IdSpec("CV"),
    models.AuditLog: IdSpec("A"),
}


ID_FIELDS: dict[type[object], str] = {
    models.Paper: "paper_id",
    models.Study: "study_id",
    models.StudyReport: "report_id",
    models.ParsedDocument: "parsed_id",
    models.Chunk: "chunk_id",
    models.EvidenceSpan: "evidence_span_id",
    models.ScreeningDecision: "decision_id",
    models.Result: "result_id",
    models.GraphNode: "node_id",
    models.GraphEdge: "edge_id",
    models.Claim: "claim_id",
    models.ClaimVerification: "verification_id",
    models.AuditLog: "audit_id",
}


def generate_stable_id(session: Session, model: type[object]) -> str:
    spec = ID_SPECS[model]
    field_name = ID_FIELDS[model]
    column = getattr(model, field_name)
    existing_ids = session.scalars(select(column).where(column.like(f"{spec.prefix}%"))).all()
    pattern = re.compile(rf"^{re.escape(spec.prefix)}(\d{{{spec.width}}})$")
    max_seen = 0
    for existing_id in existing_ids:
        match = pattern.match(str(existing_id))
        if match is not None:
            max_seen = max(max_seen, int(match.group(1)))
    return f"{spec.prefix}{max_seen + 1:0{spec.width}d}"


class BaseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()
        return instance

    def get(self, model: type[ModelT], identifier: str) -> ModelT | None:
        return self.session.get(model, identifier)

    def list_all(self, model: type[ModelT]) -> Sequence[ModelT]:
        return self.session.scalars(select(model)).all()

    def create_audit_log(
        self,
        *,
        action: str,
        target_type: str,
        target_id: str,
        actor_type: str = "system",
        actor_id: str | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> models.AuditLog:
        audit_log = models.AuditLog(
            audit_id=generate_stable_id(self.session, models.AuditLog),
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before=before,
            after=after,
        )
        return self.add(audit_log)


class PaperRepository(BaseRepository):
    def get_by_doi(self, doi: str) -> models.Paper | None:
        return self.session.scalar(select(models.Paper).where(models.Paper.doi == doi))

    def get_duplicate_candidate(
        self, *, normalized_title: str, first_author: str | None, year: int | None
    ) -> models.Paper | None:
        query = select(models.Paper).where(
            models.Paper.normalized_title == normalized_title,
            models.Paper.year == year,
        )
        for paper in self.session.scalars(query):
            authors = paper.authors or []
            candidate_first_author = authors[0] if authors else None
            if candidate_first_author == first_author:
                return paper
        return None

    def create(
        self,
        *,
        title: str,
        normalized_title: str,
        doi: str | None = None,
        pmid: str | None = None,
        pmcid: str | None = None,
        authors: list[str] | None = None,
        year: int | None = None,
        journal: str | None = None,
        abstract: str | None = None,
        source_database: str | None = None,
        source_url: str | None = None,
        full_text_available: bool = False,
    ) -> models.Paper:
        paper = models.Paper(
            paper_id=generate_stable_id(self.session, models.Paper),
            doi=doi,
            pmid=pmid,
            pmcid=pmcid,
            title=title,
            normalized_title=normalized_title,
            authors=authors or [],
            year=year,
            journal=journal,
            abstract=abstract,
            source_database=source_database,
            source_url=source_url,
            full_text_available=full_text_available,
        )
        self.add(paper)
        self.create_audit_log(
            action="paper.create",
            target_type="paper",
            target_id=paper.paper_id,
            after={"paper_id": paper.paper_id, "title": paper.title, "doi": paper.doi},
        )
        return paper


class StudyRepository(BaseRepository):
    def create(self, *, status: str = "candidate") -> models.Study:
        study = models.Study(
            study_id=generate_stable_id(self.session, models.Study),
            status=status,
            primary_outcomes=[],
        )
        self.add(study)
        self.create_audit_log(
            action="study.create",
            target_type="study",
            target_id=study.study_id,
            after={"study_id": study.study_id, "status": study.status},
        )
        return study


class StudyReportRepository(BaseRepository):
    def create(
        self,
        *,
        study_id: str,
        paper_id: str,
        report_type: str,
        confidence: float,
        evidence: str | None,
        human_review_required: bool = False,
    ) -> models.StudyReport:
        report = models.StudyReport(
            report_id=generate_stable_id(self.session, models.StudyReport),
            study_id=study_id,
            paper_id=paper_id,
            report_type=report_type,
            confidence=confidence,
            evidence=evidence,
            human_review_required=human_review_required,
        )
        self.add(report)
        self.create_audit_log(
            action="study_report.create",
            target_type="study_report",
            target_id=report.report_id,
            after={
                "report_id": report.report_id,
                "study_id": report.study_id,
                "paper_id": report.paper_id,
            },
        )
        return report


class EvidenceRepository(BaseRepository):
    def create_span(
        self,
        *,
        paper_id: str,
        text: str,
        source_format: str = "UNKNOWN",
        parser_name: str = "fixture",
        study_id: str | None = None,
        chunk_id: str | None = None,
        section: str | None = None,
        page: int | None = None,
    ) -> models.EvidenceSpan:
        span = models.EvidenceSpan(
            evidence_span_id=generate_stable_id(self.session, models.EvidenceSpan),
            paper_id=paper_id,
            study_id=study_id,
            chunk_id=chunk_id,
            source_format=source_format,
            parser_name=parser_name,
            parser_version=None,
            section=section,
            page=page,
            paragraph=None,
            figure_or_table=None,
            table_row=None,
            table_column=None,
            bbox=None,
            char_start=None,
            char_end=None,
            text=text,
            parse_confidence=None,
            source_hash=None,
        )
        return self.add(span)


class ScreeningRepository(BaseRepository):
    def create_decision(
        self,
        *,
        paper_id: str,
        level: str,
        decision: str,
        reviewer_type: str,
        study_id: str | None = None,
        reason_code: str | None = None,
        reason_text: str | None = None,
        evidence_span_id: str | None = None,
        reviewer_id: str | None = None,
        confidence: float | None = None,
    ) -> models.ScreeningDecision:
        screening_decision = models.ScreeningDecision(
            decision_id=generate_stable_id(self.session, models.ScreeningDecision),
            paper_id=paper_id,
            study_id=study_id,
            level=level,
            decision=decision,
            reason_code=reason_code,
            reason_text=reason_text,
            evidence_span_id=evidence_span_id,
            reviewer_type=reviewer_type,
            reviewer_id=reviewer_id,
            confidence=confidence,
        )
        self.add(screening_decision)
        self.create_audit_log(
            action="screening_decision.create",
            target_type="screening_decision",
            target_id=screening_decision.decision_id,
            after={
                "paper_id": paper_id,
                "level": level,
                "decision": decision,
                "confidence": confidence,
            },
        )
        return screening_decision


class ResultRepository(BaseRepository):
    def create(
        self,
        *,
        study_id: str,
        paper_id: str,
        evidence_span_id: str,
        study_type: str,
        outcome: str,
        scope: str,
        population_or_model: str | None = None,
        species: str | None = None,
        cell_line: str | None = None,
        intervention: str | None = None,
        comparator: str | None = None,
        assay: str | None = None,
        direction: str | None = None,
        effect_size: str | None = None,
        p_value: str | None = None,
        confidence_interval: str | None = None,
        sample_size: str | None = None,
        dose: str | None = None,
        duration: str | None = None,
        unit: str | None = None,
        risk_of_bias_overall: str | None = None,
        extraction_status: str = "unverified",
    ) -> models.Result:
        result = models.Result(
            result_id=generate_stable_id(self.session, models.Result),
            study_id=study_id,
            paper_id=paper_id,
            study_type=study_type,
            population_or_model=population_or_model,
            species=species,
            cell_line=cell_line,
            intervention=intervention,
            comparator=comparator,
            outcome=outcome,
            assay=assay,
            direction=direction,
            effect_size=effect_size,
            p_value=p_value,
            confidence_interval=confidence_interval,
            sample_size=sample_size,
            dose=dose,
            duration=duration,
            unit=unit,
            scope=scope,
            risk_of_bias_overall=risk_of_bias_overall,
            evidence_span_id=evidence_span_id,
            extraction_status=extraction_status,
        )
        return self.add(result)


class ClaimRepository(BaseRepository):
    def create_claim(self, *, answer_id: str, claim_text: str) -> models.Claim:
        claim = models.Claim(
            claim_id=generate_stable_id(self.session, models.Claim),
            answer_id=answer_id,
            claim_text=claim_text,
            claim_type=None,
            cited_result_ids=[],
            cited_evidence_span_ids=[],
        )
        return self.add(claim)

    def create_verification(
        self, *, claim_id: str, verdict: str, verifier_type: str
    ) -> models.ClaimVerification:
        verification = models.ClaimVerification(
            verification_id=generate_stable_id(self.session, models.ClaimVerification),
            claim_id=claim_id,
            verdict=verdict,
            reason=None,
            corrected_claim=None,
            verifier_type=verifier_type,
            verifier_version=None,
        )
        return self.add(verification)
