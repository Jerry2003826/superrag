from __future__ import annotations

import re

from ebrag.schemas.retrieval import EvidencePack
from ebrag.schemas.synthesis import AtomicClaim
from ebrag.schemas.verification import VerificationVerdict


def numeric_tokens(text: str) -> set[str]:
    return set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:e-?\d+)?%?", text, flags=re.I))


def verify_numeric_claim(claim: AtomicClaim, evidence_pack: EvidencePack) -> VerificationVerdict:
    claim_numbers = numeric_tokens(claim.text)
    if not claim_numbers:
        return VerificationVerdict(
            claim_id=claim.claim_id,
            verdict="supported",
            reason="claim contains no numeric tokens",
        )
    evidence_by_id = {span.evidence_span_id: span for span in evidence_pack.supporting_evidence}
    cited_text = " ".join(
        evidence_by_id[span_id].text
        for span_id in claim.cited_evidence_span_ids
        if span_id in evidence_by_id
    )
    cited_numbers = numeric_tokens(cited_text)
    missing = sorted(claim_numbers - cited_numbers)
    if missing:
        return VerificationVerdict(
            claim_id=claim.claim_id,
            verdict="uncited_numeric",
            reason=f"numeric tokens not found in cited evidence spans: {missing}",
            requires_human_review=True,
        )
    return VerificationVerdict(
        claim_id=claim.claim_id,
        verdict="supported",
        reason="all numeric tokens appear in cited evidence spans",
    )


def verify_numeric_claims(
    claims: list[AtomicClaim], evidence_pack: EvidencePack
) -> list[VerificationVerdict]:
    return [verify_numeric_claim(claim, evidence_pack) for claim in claims]
