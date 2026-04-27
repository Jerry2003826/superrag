from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models


class GraphRetriever:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(self, query: str, *, limit: int = 20) -> list[models.Result]:
        _ = query
        edges = self.session.scalars(
            select(models.GraphEdge).where(models.GraphEdge.edge_type == "SUPPORTED_BY")
        )
        result_ids = [
            edge.properties.get("result_id")
            for edge in edges
            if isinstance(edge.properties, dict) and edge.properties.get("result_id")
        ]
        if not result_ids:
            return []
        return list(
            self.session.scalars(
                select(models.Result).where(models.Result.result_id.in_(result_ids)).limit(limit)
            )
        )
