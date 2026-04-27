from __future__ import annotations

from ebrag.evaluation.metrics import compute_metrics
from ebrag.schemas.evaluation import EvaluationPrediction, EvaluationReport, GoldCase


def run_regression(
    *,
    gold_cases: list[GoldCase],
    predictions: list[EvaluationPrediction],
    k: int = 10,
) -> EvaluationReport:
    metrics = compute_metrics(gold_cases, predictions, k=k)
    reasons: list[str] = []
    if metrics.unsupported_claim_rate_final != 0:
        reasons.append("unsupported_claim_rate_final must be 0")
    if metrics.wrong_scope_rate_final != 0:
        reasons.append("wrong_scope_rate_final must be 0")
    if metrics.uncited_numeric_claim_rate_final != 0:
        reasons.append("uncited_numeric_claim_rate_final must be 0")
    return EvaluationReport(
        metrics=metrics,
        case_count=len(gold_cases),
        failed_release_gate_reasons=reasons,
    )
