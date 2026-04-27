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
