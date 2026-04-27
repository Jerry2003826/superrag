from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class RiskOfBiasAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_id: str
    randomization: Literal["low", "some_concerns", "high", "not_applicable"]
    blinding: Literal["low", "some_concerns", "high", "not_applicable"]
    incomplete_outcome_data: Literal["low", "some_concerns", "high", "not_applicable"]
    overall: Literal["low", "some_concerns", "high", "not_applicable"]
    rationale: str


def rob_markdown(assessments: list[RiskOfBiasAssessment]) -> str:
    lines = ["# Risk of Bias", ""]
    for assessment in assessments:
        lines.append(f"- {assessment.study_id}: {assessment.overall} - {assessment.rationale}")
    return "\n".join(lines) + "\n"
