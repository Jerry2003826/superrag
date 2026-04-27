from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.extraction import ResultNode


class EvidencePack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    route: list[str]
    eligible_results: list[ResultNode]
    supporting_evidence: list[EvidenceSpan]
    conflicting_results: list[ResultNode] = Field(default_factory=list)
    excluded_results: list[dict[str, Any]] = Field(default_factory=list)
    sufficiency: Literal["sufficient", "partial", "insufficient"]
    sufficiency_reason: str = Field(min_length=1)
