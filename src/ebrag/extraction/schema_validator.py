from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ebrag.schemas.extraction import ExtractionOutput

_RESULT_FIELDS = {
    "result_id",
    "study_id",
    "paper_id",
    "study_type",
    "population_or_model",
    "species",
    "cell_line",
    "intervention",
    "comparator",
    "outcome",
    "assay",
    "direction",
    "effect_size",
    "p_value",
    "confidence_interval",
    "sample_size",
    "dose",
    "duration",
    "unit",
    "scope",
    "evidence_span_id",
    "extraction_status",
}


def _as_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip().lower()
        return not text or text in {"none", "null", "unknown", "n/a"}
    return False


def _set_if_missing(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None and _is_missing(target.get(key)):
        target[key] = value


def _first_span_id(result: Mapping[str, Any]) -> str | None:
    span_id = _as_text(result.get("evidence_span_id"))
    if span_id is not None:
        return span_id
    span_ids = result.get("evidence_span_ids")
    if isinstance(span_ids, list):
        for item in span_ids:
            span_id = _as_text(item)
            if span_id is not None:
                return span_id
    return None


def _infer_direction(value: Any) -> str:
    text = str(value or "").lower().replace("_", " ")
    if "no significant" in text or "not significant" in text:
        return "no_significant_difference"
    if "mixed" in text:
        return "mixed"
    if "not reported" in text:
        return "not_reported"
    if any(term in text for term in ("decrease", "decreased", "decreases", "reduced", "lower")):
        return "decreased"
    if any(term in text for term in ("increase", "increased", "increases", "elevated", "higher")):
        return "increased"
    return "unclear"


def _infer_scope(*values: Any) -> str:
    text = " ".join(str(value or "") for value in values).lower()
    if any(term in text for term in ("in vitro", "cell", "cell line", "culture")):
        return "in_vitro"
    if any(term in text for term in ("mouse", "mice", "rat", "rats", "animal", "app/ps1")):
        return "animal"
    if any(term in text for term in ("clinical trial", "randomized", "rct")):
        return "clinical_trial"
    if any(term in text for term in ("human", "cohort", "observational")):
        return "observational_human"
    return "other"


def _normalize_result(
    result: Mapping[str, Any],
    *,
    index: int,
    paper_id: str | None,
    study_id_by_span: Mapping[str, str],
) -> dict[str, Any]:
    normalized = {key: value for key, value in result.items() if key in _RESULT_FIELDS}
    span_id = _first_span_id(result)
    if span_id is not None:
        _set_if_missing(normalized, "evidence_span_id", span_id)
    if paper_id is not None:
        _set_if_missing(normalized, "paper_id", paper_id)
    if span_id is not None and span_id in study_id_by_span:
        _set_if_missing(normalized, "study_id", study_id_by_span[span_id])

    subject = _as_text(result.get("subject"))
    predicate = _as_text(result.get("predicate"))
    object_ = _as_text(result.get("object"))
    context = _as_text(result.get("context"))
    value = _as_text(result.get("value"))

    _set_if_missing(normalized, "result_id", f"R{index + 1:08d}")
    if subject is not None:
        _set_if_missing(normalized, "intervention", subject)
    if object_ is not None:
        _set_if_missing(normalized, "outcome", object_)
    if value is not None:
        _set_if_missing(normalized, "effect_size", value)
    if context is not None:
        _set_if_missing(normalized, "population_or_model", context)
    _set_if_missing(normalized, "study_type", _infer_scope(context, normalized.get("study_type")))
    _set_if_missing(
        normalized,
        "direction",
        _infer_direction(normalized.get("direction") or predicate),
    )
    _set_if_missing(
        normalized,
        "scope",
        _infer_scope(context, normalized.get("study_type"), normalized.get("population_or_model")),
    )
    _set_if_missing(normalized, "extraction_status", "unverified")
    return normalized


def normalize_extraction_payload(
    payload: dict[str, Any],
    *,
    paper_id: str | None = None,
    study_id_by_span: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    for key in ("extraction", "ExtractionOutput"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            payload = nested
            break

    normalized = dict(payload)
    if paper_id is not None:
        _set_if_missing(normalized, "paper_id", paper_id)
    _set_if_missing(normalized, "extraction_status", "unverified")

    raw_results = normalized.get("results")
    if raw_results is None and isinstance(normalized.get("result"), dict):
        raw_results = [normalized["result"]]
    if isinstance(raw_results, list):
        span_map = study_id_by_span or {}
        normalized["results"] = [
            _normalize_result(
                result,
                index=index,
                paper_id=paper_id,
                study_id_by_span=span_map,
            )
            if isinstance(result, Mapping)
            else result
            for index, result in enumerate(raw_results)
        ]
    return normalized


def validate_extraction_json(
    payload: dict[str, Any],
    *,
    paper_id: str | None = None,
    study_id_by_span: Mapping[str, str] | None = None,
) -> ExtractionOutput:
    return ExtractionOutput.model_validate(
        normalize_extraction_payload(
            payload,
            paper_id=paper_id,
            study_id_by_span=study_id_by_span,
        )
    )
