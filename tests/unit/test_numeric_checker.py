from __future__ import annotations

from ebrag.extraction.numeric_checker import check_result_numbers_in_evidence
from ebrag.schemas.extraction import ResultNode


def _result(**overrides: object) -> ResultNode:
    data = {
        "result_id": "R00000001",
        "study_id": "S00000001",
        "paper_id": "P00000001",
        "study_type": "animal",
        "outcome": "IL-6",
        "direction": "decreased",
        "scope": "animal",
        "evidence_span_id": "E00000001",
    }
    data.update(overrides)
    return ResultNode.model_validate(data)


def test_numeric_checker_accepts_numbers_found_in_evidence() -> None:
    result = _result(p_value="p=0.01", dose="10 mg/kg", sample_size="n=12")

    check = check_result_numbers_in_evidence(result, "n=12 mice received 10 mg/kg, p=0.01.")

    assert check.ok
    assert check.missing_fields == ()


def test_numeric_checker_reports_missing_numeric_fields() -> None:
    result = _result(p_value="p=0.99", dose="99 mg/kg", sample_size="n=999")

    check = check_result_numbers_in_evidence(result, "n=12 mice received 10 mg/kg, p=0.01.")

    assert not check.ok
    assert set(check.missing_fields) == {"p_value", "dose", "sample_size"}
