from __future__ import annotations

from typing import Literal

from ebrag.schemas.synthesis import AtomicClaim
from ebrag.synthesis.synthesizer import SynthesisOutput


def claims_from_synthesis(output: SynthesisOutput) -> list[AtomicClaim]:
    claims: list[AtomicClaim] = []
    for index, sentence in enumerate(output.sentences, start=1):
        claim_type: Literal["numeric", "fact"] = (
            "numeric" if any(char.isdigit() for char in sentence.text) else "fact"
        )
        claims.append(
            AtomicClaim(
                claim_id=f"CLM{index:08d}",
                text=sentence.text,
                cited_result_ids=sentence.cited_result_ids,
                cited_evidence_span_ids=sentence.cited_evidence_span_ids,
                claim_type=claim_type,
            )
        )
    return claims
