from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ebrag.indexing.opensearch_index import FakeOpenSearchClient


@dataclass(frozen=True)
class LexicalRetriever:
    client: FakeOpenSearchClient
    index_name: str = "evidence_spans"

    def search(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        tokens = [token for token in query.lower().replace("-", " ").split() if len(token) > 1]
        documents = self.client.documents.get(self.index_name, {}).values()
        scored: list[tuple[int, dict[str, Any]]] = []
        for document in documents:
            haystack = f"{document.get('text', '')} {document.get('section', '')}".lower()
            score = sum(1 for token in tokens if token in haystack)
            if score:
                scored.append((score, document))
        return [doc for _, doc in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]
