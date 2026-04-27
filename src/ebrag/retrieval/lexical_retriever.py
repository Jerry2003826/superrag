from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ebrag.indexing.opensearch_index import SearchIndexClient


@dataclass(frozen=True)
class LexicalRetriever:
    client: SearchIndexClient
    index_name: str = "evidence_spans"

    def search(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        return [
            hit["payload"]
            for hit in self.client.search(index_name=self.index_name, query=query, limit=limit)
        ]
