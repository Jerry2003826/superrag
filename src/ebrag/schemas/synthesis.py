from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ebrag.schemas.ids import StableId


class AtomicClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: StableId
    text: str = Field(min_length=1)
    cited_result_ids: list[StableId]
    cited_evidence_span_ids: list[StableId]
    claim_type: Literal["fact", "numeric", "scope", "method", "interpretation", "recommendation"]
