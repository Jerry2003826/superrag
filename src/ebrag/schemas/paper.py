from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ebrag.schemas.evidence import SourceFormat
from ebrag.schemas.ids import StableId


class PaperMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: StableId | None = None
    doi: str | None = None
    pmid: str | None = None
    pmcid: str | None = None
    title: str = Field(min_length=1)
    normalized_title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=1500, le=3000)
    journal: str | None = None
    abstract: str | None = None
    source_database: str | None = None
    source_url: str | None = None


class SourceDocument(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    document_id: str = Field(min_length=1)
    paper_id: StableId
    source_format: SourceFormat
    uri: str = Field(min_length=1)
    local_path: Path | None = None
    filename: str | None = None
    content_bytes: bytes | None = None
