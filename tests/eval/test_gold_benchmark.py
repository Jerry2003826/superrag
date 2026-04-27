from __future__ import annotations

from pathlib import Path

from ebrag.evaluation.gold_cases import load_gold_cases
from ebrag.evaluation.metrics import compute_metrics
from ebrag.evaluation.regression import run_regression
from ebrag.evaluation.report import evaluation_report_to_json, evaluation_report_to_markdown
from ebrag.schemas.evaluation import EvaluationPrediction


def test_gold_cases_loader_and_metrics() -> None:
    cases = load_gold_cases(Path("tests/fixtures/gold_cases.jsonl"))
    predictions = [
        EvaluationPrediction(
            case_id="case-1",
            retrieved_result_ids=["R00000001"],
            retrieved_evidence_span_ids=["E00000001"],
            claim_verdicts=["supported"],
            final_claim_verdicts=["supported"],
        ),
        EvaluationPrediction(
            case_id="case-2",
            retrieved_result_ids=["R00000002"],
            retrieved_evidence_span_ids=["E00000002"],
            retrieved_conflicting_result_ids=["R00000003"],
            claim_verdicts=["supported"],
            final_claim_verdicts=["supported"],
        ),
    ]

    metrics = compute_metrics(cases, predictions, k=5)

    assert metrics.claim_traceability_rate == 1.0
    assert metrics.context_recall_at_k == 1.0
    assert metrics.context_precision_at_k == 1.0
    assert metrics.conflict_recall == 1.0
    assert metrics.release_gate_passed


def test_regression_report_outputs_json_and_markdown() -> None:
    cases = load_gold_cases(Path("tests/fixtures/gold_cases.jsonl"))
    report = run_regression(
        gold_cases=cases,
        predictions=[
            EvaluationPrediction(
                case_id="case-1",
                final_claim_verdicts=["unsupported"],
            )
        ],
    )

    as_json = evaluation_report_to_json(report)
    as_markdown = evaluation_report_to_markdown(report)

    assert not report.metrics.release_gate_passed
    assert "unsupported_claim_rate_final must be 0" in as_json
    assert "Release Gate Failures" in as_markdown
