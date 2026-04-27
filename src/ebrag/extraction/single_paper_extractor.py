from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.db.repositories import BaseRepository, ResultRepository
from ebrag.extraction.llm_client import LLMClient
from ebrag.extraction.numeric_checker import check_result_numbers_in_evidence
from ebrag.extraction.prompts import build_single_paper_extraction_prompt
from ebrag.extraction.schema_validator import validate_extraction_json
from ebrag.schemas.extraction import ExtractionOutput, ResultNode


class ExtractionReferenceError(ValueError):
    """Raised when LLM output references entities outside the current extraction context."""


def build_paper_context(evidence_spans: list[models.EvidenceSpan]) -> str:
    return "\n".join(
        (
            f"[{span.evidence_span_id}] study_id={span.study_id or 'unknown'} "
            f"{span.section or 'Unknown section'}: {span.text}"
        )
        for span in evidence_spans
    )


def _evidence_by_id(evidence_spans: list[models.EvidenceSpan]) -> dict[str, models.EvidenceSpan]:
    return {span.evidence_span_id: span for span in evidence_spans}


def _persist_result(
    repository: ResultRepository,
    result: ResultNode,
    *,
    extraction_status: str,
) -> models.Result:
    return repository.create(
        study_id=result.study_id,
        paper_id=result.paper_id,
        evidence_span_id=result.evidence_span_id,
        study_type=result.study_type,
        population_or_model=result.population_or_model,
        species=result.species,
        cell_line=result.cell_line,
        intervention=result.intervention,
        comparator=result.comparator,
        outcome=result.outcome,
        assay=result.assay,
        direction=result.direction,
        effect_size=result.effect_size,
        p_value=result.p_value,
        confidence_interval=result.confidence_interval,
        sample_size=result.sample_size,
        dose=result.dose,
        duration=result.duration,
        unit=result.unit,
        scope=result.scope,
        extraction_status=extraction_status,
    )


def _validate_extraction_references(
    *,
    paper_id: str,
    results: list[ResultNode],
    span_by_id: dict[str, models.EvidenceSpan],
    study_ids: set[str],
) -> None:
    errors: list[str] = []
    for result in results:
        if result.paper_id != paper_id:
            errors.append(f"{result.result_id} has paper_id={result.paper_id}, expected {paper_id}")
        if result.study_id not in study_ids:
            errors.append(f"{result.result_id} references unknown study_id={result.study_id}")
        if result.evidence_span_id not in span_by_id:
            errors.append(
                f"{result.result_id} references unknown evidence_span_id={result.evidence_span_id}"
            )

    if errors:
        msg = "Invalid extraction references: " + "; ".join(errors)
        raise ExtractionReferenceError(msg)


@dataclass(frozen=True)
class SinglePaperExtractor:
    session: Session
    llm_client: LLMClient

    def run(self, paper_id: str) -> ExtractionOutput:
        evidence_spans = list(
            self.session.scalars(
                select(models.EvidenceSpan).where(models.EvidenceSpan.paper_id == paper_id)
            )
        )
        context = build_paper_context(evidence_spans)
        prompt = build_single_paper_extraction_prompt(paper_id=paper_id, paper_context=context)
        span_by_id = _evidence_by_id(evidence_spans)
        extracted = validate_extraction_json(
            self.llm_client.complete_json(prompt=prompt, paper_id=paper_id),
            paper_id=paper_id,
            study_id_by_span={
                span.evidence_span_id: span.study_id for span in span_by_id.values()
                if span.study_id is not None
            },
        )

        study_ids = set(self.session.scalars(select(models.Study.study_id)).all())
        _validate_extraction_references(
            paper_id=paper_id,
            results=extracted.results,
            span_by_id=span_by_id,
            study_ids=study_ids,
        )

        persisted: list[models.Result] = []
        result_repository = ResultRepository(self.session)
        audit_repository = BaseRepository(self.session)
        for result in extracted.results:
            span = span_by_id.get(result.evidence_span_id)
            numeric_status = (
                check_result_numbers_in_evidence(result, span.text)
                if span is not None
                else check_result_numbers_in_evidence(result, "")
            )
            status = "verified" if numeric_status.ok else "human_required"
            persisted_result = _persist_result(result_repository, result, extraction_status=status)
            persisted.append(persisted_result)
            audit_repository.create_audit_log(
                action="extraction.result_persisted",
                target_type="result",
                target_id=persisted_result.result_id,
                after={
                    "paper_id": paper_id,
                    "evidence_span_id": result.evidence_span_id,
                    "extraction_status": status,
                    "missing_numeric_fields": list(numeric_status.missing_fields),
                },
            )

        output_status: Literal["verified", "human_required"] = "human_required" if any(
            result.extraction_status == "human_required" for result in persisted
        ) else "verified"
        return ExtractionOutput.model_validate(
            {
                "paper_id": paper_id,
                "results": [
                    {
                        "result_id": result.result_id,
                        "study_id": result.study_id,
                        "paper_id": result.paper_id,
                        "study_type": result.study_type,
                        "population_or_model": result.population_or_model,
                        "species": result.species,
                        "cell_line": result.cell_line,
                        "intervention": result.intervention,
                        "comparator": result.comparator,
                        "outcome": result.outcome,
                        "assay": result.assay,
                        "direction": result.direction or "unclear",
                        "effect_size": result.effect_size,
                        "p_value": result.p_value,
                        "confidence_interval": result.confidence_interval,
                        "sample_size": result.sample_size,
                        "dose": result.dose,
                        "duration": result.duration,
                        "unit": result.unit,
                        "scope": result.scope,
                        "evidence_span_id": result.evidence_span_id,
                        "extraction_status": result.extraction_status,
                    }
                    for result in persisted
                ],
                "extraction_status": output_status,
            }
        )
