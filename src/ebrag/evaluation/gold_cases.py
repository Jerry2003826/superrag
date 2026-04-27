from __future__ import annotations

import json
from pathlib import Path

from ebrag.schemas.evaluation import GoldCase


def load_gold_cases(path: Path) -> list[GoldCase]:
    cases: list[GoldCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(GoldCase.model_validate(json.loads(line)))
        except Exception as exc:
            msg = f"Invalid gold case at {path}:{line_number}: {exc}"
            raise ValueError(msg) from exc
    return cases
