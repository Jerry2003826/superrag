from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ebrag.schemas.ids import StableId

SourceFormat = Literal["JATS_XML", "PDF", "PDF_OCR", "SUPPLEMENT", "TEXT", "UNKNOWN"]


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(ge=1)
    x1: float = Field(ge=0)
    y1: float = Field(ge=0)
    x2: float = Field(ge=0)
    y2: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_coordinates(self) -> BoundingBox:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            msg = "Bounding box x2/y2 must be greater than x1/y1"
            raise ValueError(msg)
        return self


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_span_id: StableId
    paper_id: StableId
    study_id: StableId | None = None
    source_format: SourceFormat
    parser_name: str = Field(min_length=1)
    parser_version: str | None = None
    section: str | None = None
    page: int | None = Field(default=None, ge=1)
    paragraph: int | None = Field(default=None, ge=1)
    figure_or_table: str | None = None
    table_row: str | None = None
    table_column: str | None = None
    bbox: BoundingBox | None = None
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)
    text: str = Field(min_length=1)
    parse_confidence: float | None = Field(default=None, ge=0, le=1)
    source_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
