from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ebrag.schemas.retrieval import EvidencePack

Sufficiency = Literal["sufficient", "partial", "insufficient"]


@dataclass(frozen=True)
class SufficiencyVerdict:
    sufficiency: Sufficiency
    reason: str
    include_uncertainty_and_conflicts: bool = False


def _has_conflicting_directions(pack: EvidencePack) -> bool:
    directions = {result.direction for result in pack.eligible_results}
    positive = {"increased", "decreased"}
    negative_or_mixed = {"no_significant_difference", "mixed"}
    return bool(directions & positive) and bool(directions & negative_or_mixed)


def assess_sufficiency(
    pack: EvidencePack,
    *,
    query_scope: Literal["human_clinical", "animal", "in_vitro", "any"] = "any",
    human_evidence_policy: Literal["partial", "insufficient"] = "partial",
) -> SufficiencyVerdict:
    if not pack.eligible_results:
        return SufficiencyVerdict("insufficient", "no eligible_results")
    if not pack.supporting_evidence:
        return SufficiencyVerdict("insufficient", "no supporting_evidence")
    if pack.excluded_results and all(
        excluded.get("reason_code") == "wrong_scope" for excluded in pack.excluded_results
    ):
        return SufficiencyVerdict("insufficient", "all retrieved results are wrong_scope")
    if _has_conflicting_directions(pack) or pack.conflicting_results:
        return SufficiencyVerdict(
            "partial",
            "include_uncertainty_and_conflicts",
            include_uncertainty_and_conflicts=True,
        )
    if query_scope == "human_clinical":
        scopes = {result.scope for result in pack.eligible_results}
        if not scopes & {"observational_human", "clinical_trial"}:
            return SufficiencyVerdict(
                human_evidence_policy,
                "human clinical effect requested but only non-human evidence retrieved",
            )
    return SufficiencyVerdict("sufficient", "scope matched with supporting evidence")


def apply_sufficiency(pack: EvidencePack, verdict: SufficiencyVerdict) -> EvidencePack:
    return pack.model_copy(
        update={
            "sufficiency": verdict.sufficiency,
            "sufficiency_reason": verdict.reason,
        }
    )
