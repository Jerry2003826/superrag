from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ebrag.db import models
from ebrag.indexing.chunks import chunk_payload, evidence_span_payload


class SearchIndexClient(Protocol):
    def index(self, *, index_name: str, document_id: str, document: dict[str, Any]) -> None:
        """Index one lexical-search document."""

    def search(self, *, index_name: str, query: str, limit: int) -> list[dict[str, Any]]:
        """Search indexed documents."""


@dataclass
class FakeOpenSearchClient:
    documents: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)

    def index(self, *, index_name: str, document_id: str, document: dict[str, Any]) -> None:
        self.documents.setdefault(index_name, {})[document_id] = document

    def search(self, *, index_name: str, query: str, limit: int) -> list[dict[str, Any]]:
        tokens = [token for token in query.lower().replace("-", " ").split() if len(token) > 1]
        documents = self.documents.get(index_name, {}).values()
        scored: list[tuple[int, dict[str, Any]]] = []
        for document in documents:
            haystack = " ".join(
                str(document.get(field, ""))
                for field in ("text", "section", "paper_id", "study_id")
            ).lower()
            score = sum(1 for token in tokens if token in haystack)
            if score:
                scored.append((score, document))
        return [
            {"score": float(score), "payload": doc}
            for score, doc in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]
        ]


class OpenSearchClient:
    def __init__(self, client: Any) -> None:
        self.client = client

    @classmethod
    def from_url(cls, url: str) -> OpenSearchClient:
        from opensearchpy import OpenSearch

        return cls(OpenSearch(hosts=[url], use_ssl=url.startswith("https://")))

    def ensure_indexes(self) -> None:
        for index_name in ("chunks", "evidence_spans"):
            if not self.client.indices.exists(index=index_name):
                self.client.indices.create(
                    index=index_name,
                    body={
                        "mappings": {
                            "properties": {
                                "text": {"type": "text"},
                                "section": {"type": "text"},
                                "paper_id": {"type": "keyword"},
                                "study_id": {"type": "keyword"},
                                "chunk_id": {"type": "keyword"},
                                "evidence_span_id": {"type": "keyword"},
                                "source_format": {"type": "keyword"},
                                "verification_status": {"type": "keyword"},
                            }
                        }
                    },
                )

    def index(self, *, index_name: str, document_id: str, document: dict[str, Any]) -> None:
        self.ensure_indexes()
        self.client.index(index=index_name, id=document_id, body=document, refresh=True)

    def search(self, *, index_name: str, query: str, limit: int) -> list[dict[str, Any]]:
        self.ensure_indexes()
        response = self.client.search(
            index=index_name,
            body={
                "size": limit,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["text^4", "section^2", "paper_id", "study_id"],
                    }
                },
            },
        )
        hits = response.get("hits", {}).get("hits", [])
        return [
            {
                "score": float(hit.get("_score") or 0.0),
                "payload": hit.get("_source", {}),
            }
            for hit in hits
        ]


@dataclass(frozen=True)
class OpenSearchIndexer:
    client: SearchIndexClient
    chunk_index: str = "chunks"
    evidence_index: str = "evidence_spans"

    def index_chunk(self, chunk: models.Chunk) -> dict[str, Any]:
        payload = chunk_payload(chunk)
        self.client.index(index_name=self.chunk_index, document_id=chunk.chunk_id, document=payload)
        return payload

    def index_evidence_span(self, span: models.EvidenceSpan) -> dict[str, Any]:
        payload = evidence_span_payload(span)
        self.client.index(
            index_name=self.evidence_index,
            document_id=span.evidence_span_id,
            document=payload,
        )
        return payload
