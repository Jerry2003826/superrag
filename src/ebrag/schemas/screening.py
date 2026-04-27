from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ebrag.schemas.ids import StableId

ScreeningLevel = Literal["title_abstract", "full_text"]
ScreeningOutcome = Literal["include", "exclude", "uncertain"]
ReviewerType = Literal["rule_based", "llm", "human"]


class ScreeningDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: StableId | None = None
    paper_id: StableId
    study_id: StableId | None = None
    level: ScreeningLevel
    decision: ScreeningOutcome
    reason_code: str | None = None
    reason_text: str | None = None
    evidence_span_id: StableId | None = None
    reviewer_type: ReviewerType
    reviewer_id: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
