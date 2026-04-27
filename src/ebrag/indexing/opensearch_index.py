from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ebrag.db import models
from ebrag.indexing.chunks import chunk_payload, evidence_span_payload


class SearchIndexClient(Protocol):
    def index(self, *, index_name: str, document_id: str, document: dict[str, Any]) -> None:
        """Index one lexical-search document."""


@dataclass
class FakeOpenSearchClient:
    documents: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)

    def index(self, *, index_name: str, document_id: str, document: dict[str, Any]) -> None:
        self.documents.setdefault(index_name, {})[document_id] = document


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
