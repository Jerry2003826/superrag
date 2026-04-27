from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ebrag.schemas.evidence import EvidenceSpan, SourceFormat
from ebrag.schemas.ids import StableId

ParseStatus = Literal["parsed", "failed", "quarantined"]
ChunkType = Literal["title", "abstract", "body", "reference", "figure_caption", "table_caption"]


class ParsedChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: StableId
    paper_id: StableId
    parsed_id: StableId | None = None
    section: str | None = None
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    chunk_type: ChunkType
    text: str = Field(min_length=1)
    token_count: int | None = Field(default=None, ge=0)
    source_format: SourceFormat
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parsed_id: StableId
    paper_id: StableId
    source_format: SourceFormat
    parser_name: str = Field(min_length=1)
    parser_version: str | None = None
    object_uri: str = Field(min_length=1)
    parse_status: ParseStatus
    parse_confidence: float | None = Field(default=None, ge=0, le=1)
    qc_status: str = "pending"
    title: str | None = None
    abstract: str | None = None
    chunks: list[ParsedChunk] = Field(default_factory=list)
    evidence_candidate_spans: list[EvidenceSpan] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    source_hash: str | None = None
    error: str | None = None
