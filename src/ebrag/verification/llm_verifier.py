from __future__ import annotations

from typing import Any, Protocol

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

    def _normalize_payload(self, payload: dict[str, Any], claim_id: str) -> dict[str, Any]:
        nested = payload.get("verification")
        if isinstance(nested, dict):
            payload = nested
        payload.setdefault("claim_id", claim_id)
        verdict = payload.get("verdict")
        if isinstance(verdict, str):
            payload["verdict"] = verdict.lower().strip().replace("-", "_").replace(" ", "_")
        return payload

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
        return VerificationVerdict.model_validate(
            self._normalize_payload(payload, claim.claim_id)
        )
