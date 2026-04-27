from __future__ import annotations

from typing import Protocol

from ebrag.extraction.llm_client import StructuredJSONClient
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


class StructuredLLMVerifier:
    def __init__(self, client: StructuredJSONClient) -> None:
        self.client = client

    def verify(self, claim: AtomicClaim, evidence_text: str) -> VerificationVerdict:
        payload = self.client.verify_json(
            prompt=(
                "Verify whether the claim is supported by the evidence. "
                "Return JSON with claim_id, verdict, reason, and optional corrected_claim.\n\n"
                f"claim_id: {claim.claim_id}\n"
                f"claim: {claim.text}\n"
                f"evidence:\n{evidence_text}"
            )
        )
        payload.setdefault("claim_id", claim.claim_id)
        return VerificationVerdict.model_validate(payload)
