from __future__ import annotations

from ebrag.settings import load_settings


def test_load_default_settings() -> None:
    settings = load_settings("configs/default.yaml")

    assert settings.project.name == "evidence-bio-rag"
    assert settings.storage.raw_bucket == "raw-documents"
    assert settings.retrieval.evidence_pack_max_results == 80
