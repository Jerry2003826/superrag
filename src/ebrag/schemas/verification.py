from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ebrag.schemas.ids import StableId


class VerificationVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: StableId
    verdict: Literal[
        "supported",
        "partially_supported",
        "unsupported",
        "contradicted",
        "wrong_scope",
        "overgeneralized",
    ]
    reason: str = Field(min_length=1)
    corrected_claim: str | None = None
    requires_human_review: bool = False
