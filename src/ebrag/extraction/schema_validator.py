from __future__ import annotations

from typing import Any

from ebrag.schemas.extraction import ExtractionOutput


def validate_extraction_json(payload: dict[str, Any]) -> ExtractionOutput:
    return ExtractionOutput.model_validate(payload)
