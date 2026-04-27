from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models


class StructuredRetriever:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(self, query: str, *, limit: int = 20) -> list[models.Result]:
        tokens = [token for token in query.lower().replace("-", " ").split() if len(token) > 1]
        results = list(self.session.scalars(select(models.Result)))
        scored: list[tuple[int, models.Result]] = []
        for result in results:
            haystack = " ".join(
                value or ""
                for value in (
                    result.outcome,
                    result.intervention,
                    result.population_or_model,
                    result.species,
                    result.scope,
                    result.direction,
                )
            ).lower()
            score = sum(1 for token in tokens if token in haystack)
            if score:
                scored.append((score, result))
        ranked = sorted(scored, key=lambda item: item[0], reverse=True)[:limit]
        return [result for _, result in ranked]
