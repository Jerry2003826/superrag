from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class LLMClient(Protocol):
    def complete_json(self, *, prompt: str, paper_id: str) -> dict[str, Any]:
        """Return structured JSON for a paper extraction prompt."""


class FakeLLMClient:
    def __init__(self, fixture_by_paper_id: dict[str, dict[str, Any]]) -> None:
        self.fixture_by_paper_id = fixture_by_paper_id

    @classmethod
    def from_json_file(cls, path: Path) -> FakeLLMClient:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            msg = "Fake LLM fixture must be an object keyed by paper_id"
            raise ValueError(msg)
        return cls(data)

    def complete_json(self, *, prompt: str, paper_id: str) -> dict[str, Any]:
        _ = prompt
        if paper_id not in self.fixture_by_paper_id:
            msg = f"No fake LLM fixture for paper_id={paper_id}"
            raise KeyError(msg)
        return self.fixture_by_paper_id[paper_id]
