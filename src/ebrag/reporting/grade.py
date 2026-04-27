from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class GradeAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: str
    certainty: Literal["high", "moderate", "low", "very_low"]
    rationale: str


def grade_markdown(assessments: list[GradeAssessment]) -> str:
    lines = ["# GRADE", ""]
    for assessment in assessments:
        lines.append(f"- {assessment.outcome}: {assessment.certainty} - {assessment.rationale}")
    return "\n".join(lines) + "\n"
