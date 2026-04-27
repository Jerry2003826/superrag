from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, cast

from ebrag.db import models
from ebrag.indexing.chunks import evidence_span_payload


class EmbeddingClient(Protocol):
    def embed(self, text: str) -> list[float]:
        """Embed text."""


class VectorIndexClient(Protocol):
    def upsert(
        self,
        *,
        collection_name: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Upsert one vector point."""

    def search(
        self,
        *,
        collection_name: str,
        vector: list[float],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search vector points."""


@dataclass(frozen=True)
class FakeEmbeddingClient:
    dimensions: int = 4

    def embed(self, text: str) -> list[float]:
        base = float(len(text.split()))
        return [base + float(index) for index in range(self.dimensions)]


@dataclass
class FakeVectorClient:
    points: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)

    def upsert(
        self,
        *,
        collection_name: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        self.points.setdefault(collection_name, {})[point_id] = {
            "point_id": point_id,
            "vector": vector,
            "payload": payload,
        }

    def search(
        self,
        *,
        collection_name: str,
        vector: list[float],
        limit: int,
    ) -> list[dict[str, Any]]:
        points = list(self.points.get(collection_name, {}).values())

        def score(point: dict[str, Any]) -> float:
            point_vector = cast(list[float], point["vector"])
            return sum(left * right for left, right in zip(vector, point_vector, strict=False))

        return sorted(points, key=score, reverse=True)[:limit]


@dataclass(frozen=True)
class VectorIndexer:
    client: VectorIndexClient
    embedding_client: EmbeddingClient
    collection_name: str = "evidence_spans"

    def index_evidence_span(self, span: models.EvidenceSpan) -> dict[str, Any]:
        payload = evidence_span_payload(span)
        vector = self.embedding_client.embed(span.text)
        self.client.upsert(
            collection_name=self.collection_name,
            point_id=span.evidence_span_id,
            vector=vector,
            payload=payload,
        )
        return payload
