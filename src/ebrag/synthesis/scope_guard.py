from __future__ import annotations

from typing import Literal

from ebrag.schemas.extraction import ResultNode

ClaimScope = Literal["in_vitro", "animal", "human_clinical", "biomarker", "clinical_efficacy"]


def is_scope_overreach(*, result: ResultNode, requested_scope: ClaimScope) -> bool:
    if requested_scope == "animal" and result.scope == "in_vitro":
        return True
    if requested_scope == "human_clinical" and result.scope in {"in_vitro", "animal"}:
        return True
    return requested_scope == "clinical_efficacy" and result.outcome.lower() in {
        "il-6",
        "tnf-alpha",
        "biomarker",
    }
