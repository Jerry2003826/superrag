from __future__ import annotations

import json

from ebrag.schemas.evaluation import EvaluationReport


def evaluation_report_to_json(report: EvaluationReport) -> str:
    return json.dumps(report.model_dump(), indent=2, sort_keys=True)


def evaluation_report_to_markdown(report: EvaluationReport) -> str:
    metrics = report.metrics
    lines = [
        "# Evaluation Report",
        "",
        f"Cases: {report.case_count}",
        f"Release gate: {'PASS' if metrics.release_gate_passed else 'FAIL'}",
        "",
        "## Metrics",
        "",
    ]
    for key, value in metrics.model_dump().items():
        lines.append(f"- {key}: {value}")
    if report.failed_release_gate_reasons:
        lines.extend(["", "## Release Gate Failures", ""])
        lines.extend(f"- {reason}" for reason in report.failed_release_gate_reasons)
    return "\n".join(lines) + "\n"
