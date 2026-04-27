from __future__ import annotations

from dataclasses import dataclass

from ebrag.db import models


@dataclass(frozen=True)
class FakeReranker:
    def rerank_results(
        self,
        *,
        query: str,
        results: list[models.Result],
        limit: int,
    ) -> list[models.Result]:
        tokens = [token for token in query.lower().replace("-", " ").split() if len(token) > 1]

        def score(result: models.Result) -> int:
            text = " ".join(
                value or ""
                for value in (
                    result.outcome,
                    result.intervention,
                    result.scope,
                    result.evidence_span.text if result.evidence_span else "",
                )
            ).lower()
            return sum(1 for token in tokens if token in text)

        return sorted(results, key=score, reverse=True)[:limit]
