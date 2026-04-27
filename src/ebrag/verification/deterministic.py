from __future__ import annotations

from ebrag.schemas.retrieval import EvidencePack
from ebrag.schemas.synthesis import AtomicClaim
from ebrag.schemas.verification import VerificationVerdict


def verify_citation_ids(claim: AtomicClaim, evidence_pack: EvidencePack) -> VerificationVerdict:
    result_ids = {result.result_id for result in evidence_pack.eligible_results}
    evidence_span_ids = {span.evidence_span_id for span in evidence_pack.supporting_evidence}
    missing_results = [
        result_id for result_id in claim.cited_result_ids if result_id not in result_ids
    ]
    missing_spans = [
        span_id for span_id in claim.cited_evidence_span_ids if span_id not in evidence_span_ids
    ]
    if not claim.cited_result_ids or not claim.cited_evidence_span_ids:
        return VerificationVerdict(
            claim_id=claim.claim_id,
            verdict="unsupported",
            reason="claim is missing required result or evidence span citations",
        )
    if missing_results or missing_spans:
        return VerificationVerdict(
            claim_id=claim.claim_id,
            verdict="unsupported",
            reason=(
                "claim cites unknown ids: "
                f"results={missing_results or []}; evidence_spans={missing_spans or []}"
            ),
        )
    return VerificationVerdict(
        claim_id=claim.claim_id,
        verdict="supported",
        reason="all cited result and evidence span ids exist in the EvidencePack",
    )


def verify_claims_deterministically(
    claims: list[AtomicClaim], evidence_pack: EvidencePack
) -> list[VerificationVerdict]:
    return [verify_citation_ids(claim, evidence_pack) for claim in claims]
