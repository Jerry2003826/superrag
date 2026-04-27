from __future__ import annotations

from ebrag.schemas.retrieval import EvidencePack
from ebrag.schemas.synthesis import AtomicClaim
from ebrag.schemas.verification import VerificationVerdict
from ebrag.verification.deterministic import verify_citation_ids


def check_claim_citations(
    claims: list[AtomicClaim], evidence_pack: EvidencePack
) -> list[VerificationVerdict]:
    return [verify_citation_ids(claim, evidence_pack) for claim in claims]
