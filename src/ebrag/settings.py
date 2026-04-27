from __future__ import annotations

import os
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

_YAML_SETTINGS: ContextVar[dict[str, Any] | None] = ContextVar(
    "_YAML_SETTINGS", default=None
)


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        _ = field
        yaml_settings = _YAML_SETTINGS.get() or {}
        return yaml_settings.get(field_name), field_name, True

    def __call__(self) -> dict[str, Any]:
        return _YAML_SETTINGS.get() or {}


class ProjectSettings(BaseModel):
    name: str = "evidence-bio-rag"
    environment: str = "dev"


class DatabaseSettings(BaseModel):
    url: str = "sqlite+pysqlite:///./ebrag-dev.sqlite3"


class ServicesSettings(BaseModel):
    opensearch_url: str = "http://localhost:9200"
    qdrant_url: str = "http://localhost:6333"
    neo4j_url: str = "bolt://localhost:7687"
    minio_endpoint: str = "localhost:9000"
    redis_url: str = "redis://localhost:6379/0"
    grobid_url: str = "http://localhost:8070"


class LLMSettings(BaseModel):
    provider: Literal["fake", "openai", "anthropic", "google"] = "fake"
    api_key: str | None = None
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=2, ge=0)


class EmbeddingSettings(BaseModel):
    provider: Literal["fake", "sentence_transformers"] = "fake"
    model: str = "BAAI/bge-small-en-v1.5"


class VectorSettings(BaseModel):
    collection: str = "evidence_spans"


class RerankerSettings(BaseModel):
    provider: Literal["simple"] = "simple"


class StorageSettings(BaseModel):
    object_store: Literal["minio", "s3", "local"] = "local"
    raw_bucket: str = "raw-documents"
    parsed_bucket: str = "parsed-documents"
    page_image_bucket: str = "page-images"
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_secure: bool = False
    local_root: str = ".local-object-store"


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


def _csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class SecuritySettings(BaseModel):
    api_key: str | None = None
    api_key_header: str = "X-API-Key"
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    cors_methods: str = "GET,POST,OPTIONS"
    cors_headers: str = "Content-Type,Authorization,X-API-Key"
    rate_limit_enabled: bool = True
    rate_limit_default: str = "120/minute"
    rate_limit_query: str = "30/minute"
    rate_limit_ingestion: str = "10/minute"
    rate_limit_admin: str = "5/hour"
    upload_max_bytes: int = Field(default=50 * 1024 * 1024, gt=0)

    @property
    def cors_origin_list(self) -> list[str]:
        return _csv_values(self.cors_origins)

    @property
    def cors_method_list(self) -> list[str]:
        return _csv_values(self.cors_methods)

    @property
    def cors_header_list(self) -> list[str]:
        return _csv_values(self.cors_headers)


def _is_placeholder_secret(value: str | None) -> bool:
    if value is None:
        return True
    cleaned = value.strip().lower()
    return (
        cleaned == ""
        or cleaned in {"change-me", "changeme", "replace-me", "replace_me"}
        or cleaned.startswith("replace-with")
        or cleaned.startswith("<")
    )


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
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    vector: VectorSettings = Field(default_factory=VectorSettings)
    reranker: RerankerSettings = Field(default_factory=RerankerSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    parsing: ParsingSettings = Field(default_factory=ParsingSettings)
    screening: ScreeningSettings = Field(default_factory=ScreeningSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    synthesis: SynthesisSettings = Field(default_factory=SynthesisSettings)
    verification: VerificationSettings = Field(default_factory=VerificationSettings)
    evaluation: EvaluationSettings = Field(default_factory=EvaluationSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    @model_validator(mode="after")
    def validate_production_providers(self) -> AppSettings:
        if self.project.environment.lower() in {"prod", "production"}:
            fake_providers = []
            if self.llm.provider == "fake":
                fake_providers.append("llm")
            if self.embedding.provider == "fake":
                fake_providers.append("embedding")
            if fake_providers:
                joined = ", ".join(fake_providers)
                msg = f"Production environment cannot use fake providers: {joined}"
                raise ValueError(msg)
            if _is_placeholder_secret(self.security.api_key):
                msg = "Production environment requires EBRAG_SECURITY__API_KEY"
                raise ValueError(msg)
            if "*" in self.security.cors_origin_list:
                msg = "Production environment cannot use wildcard CORS origins"
                raise ValueError(msg)
        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


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
    env_config_path = os.environ.get("EBRAG_CONFIG")
    selected_path = config_path or env_config_path or "configs/default.yaml"
    path = Path(selected_path)
    token = _YAML_SETTINGS.set(_read_yaml_config(path))
    try:
        return AppSettings()
    finally:
        _YAML_SETTINGS.reset(token)
