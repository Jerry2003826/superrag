from __future__ import annotations

from typing import Any


def to_ragas_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "question": case.get("query", ""),
            "contexts": case.get("contexts", []),
            "answer": case.get("answer", ""),
            "ground_truth": case.get("ground_truth", ""),
        }
        for case in cases
    ]
