from __future__ import annotations

from collections import Counter

from ebrag.schemas.evaluation import EvaluationMetrics, EvaluationPrediction, GoldCase


def _rate(count: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else count / denominator


def _mean(values: list[float]) -> float:
    return 0.0 if not values else sum(values) / len(values)


def _verdict_rate(predictions: list[EvaluationPrediction], verdict: str, *, final: bool) -> float:
    verdicts: list[str] = []
    for prediction in predictions:
        verdicts.extend(prediction.final_claim_verdicts if final else prediction.claim_verdicts)
    counts = Counter(verdicts)
    return _rate(counts[verdict], len(verdicts))


def compute_metrics(
    gold_cases: list[GoldCase],
    predictions: list[EvaluationPrediction],
    *,
    k: int = 10,
) -> EvaluationMetrics:
    predictions_by_case = {prediction.case_id: prediction for prediction in predictions}
    traceable = 0
    claim_count = 0
    recalls: list[float] = []
    precisions: list[float] = []
    conflict_recalls: list[float] = []

    for gold in gold_cases:
        prediction = predictions_by_case.get(gold.case_id)
        if prediction is None:
            recalls.append(0.0)
            precisions.append(0.0)
            conflict_recalls.append(0.0 if gold.expected_conflict_result_ids else 1.0)
            continue

        claim_count += len(prediction.claim_verdicts)
        traceable += sum(
            1
            for _ in prediction.claim_verdicts
            if prediction.retrieved_result_ids and prediction.retrieved_evidence_span_ids
        )

        expected_evidence = set(gold.expected_evidence_span_ids)
        retrieved_evidence = prediction.retrieved_evidence_span_ids[:k]
        retrieved_evidence_set = set(retrieved_evidence)
        recalls.append(
            _rate(len(expected_evidence & retrieved_evidence_set), len(expected_evidence))
            if expected_evidence
            else 1.0
        )
        precisions.append(
            _rate(len(expected_evidence & retrieved_evidence_set), len(retrieved_evidence))
        )

        expected_conflicts = set(gold.expected_conflict_result_ids)
        retrieved_conflicts = set(prediction.retrieved_conflicting_result_ids)
        conflict_recalls.append(
            _rate(len(expected_conflicts & retrieved_conflicts), len(expected_conflicts))
            if expected_conflicts
            else 1.0
        )

    unsupported_final = _verdict_rate(predictions, "unsupported", final=True)
    wrong_scope_final = _verdict_rate(predictions, "wrong_scope", final=True)
    uncited_numeric_final = _verdict_rate(predictions, "uncited_numeric", final=True)
    return EvaluationMetrics(
        claim_traceability_rate=_rate(traceable, claim_count),
        unsupported_claim_rate=_verdict_rate(predictions, "unsupported", final=False),
        wrong_scope_rate=_verdict_rate(predictions, "wrong_scope", final=False),
        uncited_numeric_claim_rate=_verdict_rate(predictions, "uncited_numeric", final=False),
        unsupported_claim_rate_final=unsupported_final,
        wrong_scope_rate_final=wrong_scope_final,
        uncited_numeric_claim_rate_final=uncited_numeric_final,
        context_recall_at_k=_mean(recalls),
        context_precision_at_k=_mean(precisions),
        conflict_recall=_mean(conflict_recalls),
        release_gate_passed=(
            unsupported_final == 0.0
            and wrong_scope_final == 0.0
            and uncited_numeric_final == 0.0
        ),
    )
