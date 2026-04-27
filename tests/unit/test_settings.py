from __future__ import annotations

from pathlib import Path

import pytest

from ebrag.settings import load_settings


def test_load_default_settings() -> None:
    settings = load_settings("configs/default.yaml")

    assert settings.project.name == "evidence-bio-rag"
    assert settings.storage.raw_bucket == "raw-documents"
    assert settings.retrieval.evidence_pack_max_results == 80


def test_environment_overrides_yaml_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "database:\n"
        "  url: postgresql+psycopg://yaml:yaml@localhost:5432/yaml\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EBRAG_DATABASE__URL", "sqlite+pysqlite:///override.db")

    load_settings.cache_clear()
    try:
        settings = load_settings(config_path)
    finally:
        load_settings.cache_clear()

    assert settings.database.url == "sqlite+pysqlite:///override.db"


def test_production_rejects_fake_runtime_providers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "project:\n"
        "  environment: prod\n"
        "llm:\n"
        "  provider: fake\n"
        "embedding:\n"
        "  provider: fake\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EBRAG_PROJECT__ENVIRONMENT", "prod")
    monkeypatch.setenv("EBRAG_LLM__PROVIDER", "fake")
    monkeypatch.setenv("EBRAG_EMBEDDING__PROVIDER", "fake")

    load_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="Production environment cannot use fake providers"):
            load_settings(config_path)
    finally:
        load_settings.cache_clear()


def test_production_requires_deployment_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "project:\n"
        "  environment: prod\n"
        "llm:\n"
        "  provider: openai\n"
        "embedding:\n"
        "  provider: sentence_transformers\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EBRAG_PROJECT__ENVIRONMENT", "prod")
    monkeypatch.setenv("EBRAG_LLM__PROVIDER", "openai")
    monkeypatch.setenv("EBRAG_EMBEDDING__PROVIDER", "sentence_transformers")

    load_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="requires EBRAG_SECURITY__API_KEY"):
            load_settings(config_path)
    finally:
        load_settings.cache_clear()


def test_production_rejects_wildcard_cors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "project:\n"
        "  environment: prod\n"
        "llm:\n"
        "  provider: openai\n"
        "embedding:\n"
        "  provider: sentence_transformers\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EBRAG_PROJECT__ENVIRONMENT", "prod")
    monkeypatch.setenv("EBRAG_LLM__PROVIDER", "openai")
    monkeypatch.setenv("EBRAG_EMBEDDING__PROVIDER", "sentence_transformers")
    monkeypatch.setenv("EBRAG_SECURITY__API_KEY", "test-secret")
    monkeypatch.setenv("EBRAG_SECURITY__CORS_ORIGINS", "*")

    load_settings.cache_clear()
    try:
        with pytest.raises(ValueError, match="wildcard CORS"):
            load_settings(config_path)
    finally:
        load_settings.cache_clear()
