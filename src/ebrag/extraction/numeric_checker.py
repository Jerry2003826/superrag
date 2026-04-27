from __future__ import annotations

import re
from dataclasses import dataclass

from ebrag.schemas.extraction import ResultNode


@dataclass(frozen=True)
class NumericCheckResult:
    ok: bool
    missing_fields: tuple[str, ...]


def _numeric_tokens(value: str | None) -> set[str]:
    if value is None:
        return set()
    return set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:e-?\d+)?%?", value, flags=re.I))


def check_result_numbers_in_evidence(result: ResultNode, evidence_text: str) -> NumericCheckResult:
    missing: list[str] = []
    evidence_tokens = _numeric_tokens(evidence_text)
    for field in ("p_value", "dose", "sample_size"):
        value = getattr(result, field)
        tokens = _numeric_tokens(value)
        if tokens and not tokens.issubset(evidence_tokens):
            missing.append(field)
    return NumericCheckResult(ok=not missing, missing_fields=tuple(missing))
