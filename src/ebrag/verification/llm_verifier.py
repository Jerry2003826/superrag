from __future__ import annotations

from typing import Protocol

from ebrag.schemas.synthesis import AtomicClaim
from ebrag.schemas.verification import VerificationVerdict


class LLMVerifier(Protocol):
    def verify(self, claim: AtomicClaim, evidence_text: str) -> VerificationVerdict:
        """Verify a claim against evidence text."""


class FakeLLMVerifier:
    def verify(self, claim: AtomicClaim, evidence_text: str) -> VerificationVerdict:
        _ = evidence_text
        return VerificationVerdict(
            claim_id=claim.claim_id,
            verdict="supported",
            reason="fake verifier accepts deterministic fixture evidence",
        )
