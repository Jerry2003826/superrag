from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProjectSettings(BaseModel):
    name: str = "evidence-bio-rag"
    environment: str = "dev"


class DatabaseSettings(BaseModel):
    url: str = "postgresql+psycopg://ebrag:ebrag@localhost:5432/ebrag"


class ServicesSettings(BaseModel):
    opensearch_url: str = "http://localhost:9200"
    qdrant_url: str = "http://localhost:6333"
    neo4j_url: str = "bolt://localhost:7687"
    minio_endpoint: str = "localhost:9000"
    redis_url: str = "redis://localhost:6379/0"
    grobid_url: str = "http://localhost:8070"


class StorageSettings(BaseModel):
    object_store: Literal["minio", "s3", "local"] = "minio"
    raw_bucket: str = "raw-documents"
    parsed_bucket: str = "parsed-documents"
    page_image_bucket: str = "page-images"


class ParsingSettings(BaseModel):
    prefer_xml: bool = True
    enable_grobid: bool = True
    enable_docling: bool = False
    enable_marker: bool = False
    enable_mistral_ocr: bool = False
    enable_paddleocr: bool = False
    require_provenance: bool = True
    quarantine_on_missing_metadata: bool = True


class ScreeningSettings(BaseModel):
    active_learning_enabled: bool = True
    uncertain_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    human_review_required_for_exclusion: bool = True


class RetrievalSettings(BaseModel):
    lexical_top_k: int = Field(default=100, gt=0)
    vector_top_k: int = Field(default=100, gt=0)
    graph_top_k: int = Field(default=100, gt=0)
    rerank_top_k: int = Field(default=30, gt=0)
    evidence_pack_max_results: int = Field(default=80, gt=0)
    require_conflict_search: bool = True


class SynthesisSettings(BaseModel):
    allow_raw_chunk_synthesis: bool = False
    require_result_ids: bool = True
    require_evidence_span_ids: bool = True
    abstain_on_insufficient_evidence: bool = True


class VerificationSettings(BaseModel):
    unsupported_claim_policy: Literal["block", "warn"] = "block"
    numeric_claim_policy: Literal["block_if_uncited", "warn"] = "block_if_uncited"
    wrong_scope_policy: Literal["block", "warn"] = "block"
    high_risk_human_review: bool = True


class EvaluationSettings(BaseModel):
    final_unsupported_claim_target: int = 0
    final_wrong_scope_target: int = 0
    final_uncited_numeric_target: int = 0


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_prefix="EBRAG_",
        extra="ignore",
    )

    project: ProjectSettings = Field(default_factory=ProjectSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    services: ServicesSettings = Field(default_factory=ServicesSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    parsing: ParsingSettings = Field(default_factory=ParsingSettings)
    screening: ScreeningSettings = Field(default_factory=ScreeningSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    synthesis: SynthesisSettings = Field(default_factory=SynthesisSettings)
    verification: VerificationSettings = Field(default_factory=VerificationSettings)
    evaluation: EvaluationSettings = Field(default_factory=EvaluationSettings)


def _read_yaml_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        msg = f"Configuration file must contain a mapping: {path}"
        raise ValueError(msg)
    return cast(dict[str, Any], loaded)


@lru_cache(maxsize=8)
def load_settings(config_path: str | Path | None = None) -> AppSettings:
    path = Path(config_path) if config_path is not None else Path("configs/default.yaml")
    return AppSettings(**_read_yaml_config(path))
