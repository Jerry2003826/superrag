from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GoldCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    expected_result_ids: list[str] = Field(default_factory=list)
    expected_evidence_span_ids: list[str] = Field(default_factory=list)
    expected_conflict_result_ids: list[str] = Field(default_factory=list)


class EvaluationPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    retrieved_result_ids: list[str] = Field(default_factory=list)
    retrieved_evidence_span_ids: list[str] = Field(default_factory=list)
    retrieved_conflicting_result_ids: list[str] = Field(default_factory=list)
    claim_verdicts: list[str] = Field(default_factory=list)
    final_claim_verdicts: list[str] = Field(default_factory=list)


class EvaluationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_traceability_rate: float
    unsupported_claim_rate: float
    wrong_scope_rate: float
    uncited_numeric_claim_rate: float
    unsupported_claim_rate_final: float
    wrong_scope_rate_final: float
    uncited_numeric_claim_rate_final: float
    context_recall_at_k: float
    context_precision_at_k: float
    conflict_recall: float
    release_gate_passed: bool


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: EvaluationMetrics
    case_count: int
    failed_release_gate_reasons: list[str] = Field(default_factory=list)
