from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, cast
from uuid import NAMESPACE_URL, uuid5

from ebrag.db import models
from ebrag.indexing.chunks import evidence_span_payload


class EmbeddingClient(Protocol):
    @property
    def dimensions(self) -> int:
        """Embedding vector dimensions."""

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


class SentenceTransformerEmbeddingClient:
    def __init__(self, model_name: str | None = None, model: Any | None = None) -> None:
        self.model_name = model_name or "BAAI/bge-small-en-v1.5"
        self._model = model
        self._dimensions: int | None = getattr(model, "dimensions", None)

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimensions(self) -> int:
        if self._dimensions is not None:
            return self._dimensions
        getter = getattr(self.model, "get_sentence_embedding_dimension", None)
        if callable(getter):
            dimension = getter()
            if isinstance(dimension, int):
                self._dimensions = dimension
                return dimension
        self._dimensions = len(self.embed("__dimension_probe__"))
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        if not text.strip():
            msg = "Cannot embed empty text"
            raise ValueError(msg)
        encoded = self.model.encode(text, normalize_embeddings=True)
        vector = encoded.tolist() if hasattr(encoded, "tolist") else encoded
        return [float(value) for value in vector]


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


class QdrantVectorClient:
    def __init__(self, client: Any, *, dimensions: int) -> None:
        self.client = client
        self.dimensions = dimensions

    @classmethod
    def from_url(cls, url: str, *, dimensions: int) -> QdrantVectorClient:
        from qdrant_client import QdrantClient

        return cls(QdrantClient(url=url), dimensions=dimensions)

    def _ensure_collection(self, collection_name: str) -> None:
        from qdrant_client import models as qdrant_models

        exists = (
            self.client.collection_exists(collection_name)
            if hasattr(self.client, "collection_exists")
            else False
        )
        if not exists:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=self.dimensions,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

    def _point_id(self, point_id: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"evidence-bio-rag:{point_id}"))

    def upsert(
        self,
        *,
        collection_name: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        from qdrant_client import models as qdrant_models

        self._ensure_collection(collection_name)
        self.client.upsert(
            collection_name=collection_name,
            points=[
                qdrant_models.PointStruct(
                    id=self._point_id(point_id),
                    vector=vector,
                    payload=payload,
                )
            ],
        )

    def search(
        self,
        *,
        collection_name: str,
        vector: list[float],
        limit: int,
    ) -> list[dict[str, Any]]:
        self._ensure_collection(collection_name)
        if hasattr(self.client, "search"):
            hits = self.client.search(
                collection_name=collection_name,
                query_vector=vector,
                limit=limit,
            )
        else:
            response = self.client.query_points(
                collection_name=collection_name,
                query=vector,
                limit=limit,
            )
            hits = getattr(response, "points", response)
        return [
            {
                "point_id": str(
                    (getattr(hit, "payload", {}) or {}).get("evidence_span_id", hit.id)
                ),
                "score": float(getattr(hit, "score", 0.0)),
                "payload": getattr(hit, "payload", {}) or {},
            }
            for hit in hits
        ]


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
