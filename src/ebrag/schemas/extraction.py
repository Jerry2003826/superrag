from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ebrag.schemas.ids import StableId

Direction = Literal[
    "increased",
    "decreased",
    "no_significant_difference",
    "mixed",
    "not_reported",
    "unclear",
]
Scope = Literal["in_vitro", "animal", "observational_human", "clinical_trial", "other"]
ExtractionStatus = Literal["unverified", "verified", "conflict", "human_required"]


class ResultNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: StableId
    study_id: StableId
    paper_id: StableId
    study_type: str = Field(min_length=1)
    population_or_model: str | None = None
    species: str | None = None
    cell_line: str | None = None
    intervention: str | None = None
    comparator: str | None = None
    outcome: str = Field(min_length=1)
    assay: str | None = None
    direction: Direction
    effect_size: str | None = None
    p_value: str | None = None
    confidence_interval: str | None = None
    sample_size: str | None = None
    dose: str | None = None
    duration: str | None = None
    unit: str | None = None
    scope: Scope
    evidence_span_id: StableId
    extraction_status: ExtractionStatus = "unverified"


class ExtractionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: StableId
    results: list[ResultNode]
    extraction_status: ExtractionStatus = "unverified"
