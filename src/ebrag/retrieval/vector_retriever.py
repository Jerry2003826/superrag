from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ebrag.indexing.vector_index import EmbeddingClient, VectorIndexClient


@dataclass(frozen=True)
class VectorRetriever:
    client: VectorIndexClient
    embedding_client: EmbeddingClient
    collection_name: str = "evidence_spans"

    def search(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        vector = self.embedding_client.embed(query)
        return self.client.search(
            collection_name=self.collection_name,
            vector=vector,
            limit=limit,
        )
