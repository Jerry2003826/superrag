from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

import pytest

from ebrag.indexing.opensearch_index import OpenSearchClient
from ebrag.indexing.vector_index import QdrantVectorClient, SentenceTransformerEmbeddingClient
from ebrag.storage.minio_store import MinioStore


class _StoredObject:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        pass

    def release_conn(self) -> None:
        pass


@dataclass
class _FakeMinioClient:
    buckets: set[str] = field(default_factory=set)
    objects: dict[tuple[str, str], bytes] = field(default_factory=dict)

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        self.buckets.add(bucket)

    def put_object(
        self,
        bucket: str,
        key: str,
        data: BytesIO,
        length: int,
        content_type: str | None = None,
    ) -> None:
        _ = content_type
        self.objects[(bucket, key)] = data.read(length)

    def get_object(self, bucket: str, key: str) -> _StoredObject:
        return _StoredObject(self.objects[(bucket, key)])

    def stat_object(self, bucket: str, key: str) -> object:
        if (bucket, key) not in self.objects:
            raise KeyError(key)
        return object()


def test_minio_store_creates_bucket_and_round_trips_bytes() -> None:
    client = _FakeMinioClient()
    store = MinioStore(
        endpoint="localhost:9000",
        access_key="minio",
        secret_key="minio123",
        client=client,
    )

    uri = store.put_bytes("raw-documents", "papers/doc.xml", b"<article />")

    assert uri == "minio://raw-documents/papers/doc.xml"
    assert client.buckets == {"raw-documents"}
    assert store.exists("raw-documents", "papers/doc.xml") is True
    assert store.get_bytes("raw-documents", "papers/doc.xml") == b"<article />"


class _FakeIndices:
    def __init__(self) -> None:
        self.created: dict[str, dict[str, Any]] = {}

    def exists(self, index: str) -> bool:
        return index in self.created

    def create(self, index: str, body: dict[str, Any]) -> None:
        self.created[index] = body


class _FakeOpenSearch:
    def __init__(self) -> None:
        self.indices = _FakeIndices()
        self.indexed: list[dict[str, Any]] = []

    def index(self, *, index: str, id: str, body: dict[str, Any], refresh: bool) -> None:
        self.indexed.append({"index": index, "id": id, "body": body, "refresh": refresh})

    def search(self, *, index: str, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "hits": {
                "hits": [
                    {
                        "_score": 2.5,
                        "_source": {
                            "evidence_span_id": "E00000001",
                            "text": "Compound X reduced IL-6.",
                        },
                    }
                ]
            }
        }


def test_opensearch_client_ensures_indexes_indexes_and_searches() -> None:
    raw_client = _FakeOpenSearch()
    client = OpenSearchClient(raw_client)

    client.ensure_indexes()
    client.index(
        index_name="evidence_spans",
        document_id="E00000001",
        document={"text": "Compound X reduced IL-6.", "section": "Results"},
    )
    hits = client.search(index_name="evidence_spans", query="Compound X IL-6", limit=3)

    assert {"chunks", "evidence_spans"} <= set(raw_client.indices.created)
    assert raw_client.indexed[0]["id"] == "E00000001"
    assert hits[0]["payload"]["evidence_span_id"] == "E00000001"
    assert hits[0]["score"] == 2.5


@dataclass
class _FakeSentenceTransformer:
    dimensions: int = 3

    def encode(self, text: str, normalize_embeddings: bool = True) -> list[float]:
        _ = normalize_embeddings
        return [float(len(text)), 1.0, 0.5]


def test_sentence_transformer_embedding_client_has_stable_dimensions() -> None:
    client = SentenceTransformerEmbeddingClient(model=_FakeSentenceTransformer())

    assert client.dimensions == 3
    assert client.embed("hello") == [5.0, 1.0, 0.5]
    with pytest.raises(ValueError, match="empty text"):
        client.embed("  ")


class _FakeQdrant:
    def __init__(self) -> None:
        self.collections: dict[str, int] = {}
        self.upserts: list[Any] = []

    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def create_collection(self, collection_name: str, vectors_config: Any) -> None:
        self.collections[collection_name] = vectors_config.size

    def upsert(self, collection_name: str, points: list[Any]) -> None:
        self.upserts.append((collection_name, points))

    def search(self, collection_name: str, query_vector: list[float], limit: int) -> list[Any]:
        _ = query_vector

        class Hit:
            id = "E00000001"
            score = 0.9
            payload = {"evidence_span_id": "E00000001", "text": "Compound X reduced IL-6."}

        return [Hit()][:limit]


def test_qdrant_vector_client_ensures_collection_upserts_and_searches() -> None:
    raw_client = _FakeQdrant()
    client = QdrantVectorClient(raw_client, dimensions=3)

    client.upsert(
        collection_name="evidence_spans",
        point_id="E00000001",
        vector=[0.1, 0.2, 0.3],
        payload={"text": "Compound X reduced IL-6."},
    )
    hits = client.search(collection_name="evidence_spans", vector=[0.1, 0.2, 0.3], limit=1)

    assert raw_client.collections["evidence_spans"] == 3
    assert raw_client.upserts[0][0] == "evidence_spans"
    assert raw_client.upserts[0][1][0].id != "E00000001"
    assert hits[0]["point_id"] == "E00000001"
    assert hits[0]["payload"]["evidence_span_id"] == "E00000001"
