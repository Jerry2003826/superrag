from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from ebrag.extraction.llm_client import (
    AnthropicJSONClient,
    FakeLLMClient,
    GoogleJSONClient,
    LLMClient,
    OpenAICompatibleJSONClient,
    StructuredJSONClient,
)
from ebrag.indexing.graph_index import GraphIndexer
from ebrag.indexing.opensearch_index import (
    FakeOpenSearchClient,
    OpenSearchClient,
    OpenSearchIndexer,
)
from ebrag.indexing.vector_index import (
    EmbeddingClient,
    FakeEmbeddingClient,
    FakeVectorClient,
    QdrantVectorClient,
    SentenceTransformerEmbeddingClient,
    VectorIndexClient,
    VectorIndexer,
)
from ebrag.retrieval.graph_retriever import GraphRetriever
from ebrag.retrieval.lexical_retriever import LexicalRetriever
from ebrag.retrieval.reranker import FakeReranker
from ebrag.retrieval.structured_retriever import StructuredRetriever
from ebrag.retrieval.vector_retriever import VectorRetriever
from ebrag.settings import AppSettings, load_settings
from ebrag.storage.local_store import LocalStore
from ebrag.storage.minio_store import MinioStore
from ebrag.storage.object_store import ObjectStore


def _require_api_key(provider: str, api_key: str | None) -> str:
    if api_key:
        return api_key
    msg = f"EBRAG_LLM__API_KEY is required for {provider} provider"
    raise ValueError(msg)


def _require_setting(name: str, value: str | None) -> str:
    if value:
        return value
    msg = f"{name} is required"
    raise ValueError(msg)


def build_structured_llm_client(settings: AppSettings | None = None) -> StructuredJSONClient:
    resolved = settings or load_settings()
    llm = resolved.llm
    if llm.provider == "fake":
        msg = "fake provider does not have a structured runtime client"
        raise ValueError(msg)
    api_key = _require_api_key(llm.provider, llm.api_key)
    if llm.provider == "openai":
        return OpenAICompatibleJSONClient(
            api_key=api_key,
            model=llm.model,
            base_url=llm.base_url,
            timeout_seconds=llm.timeout_seconds,
            max_retries=llm.max_retries,
        )
    if llm.provider == "anthropic":
        return AnthropicJSONClient(
            api_key=api_key,
            model=llm.model,
            timeout_seconds=llm.timeout_seconds,
            max_retries=llm.max_retries,
        )
    if llm.provider == "google":
        return GoogleJSONClient(
            api_key=api_key,
            model=llm.model,
            timeout_seconds=llm.timeout_seconds,
            max_retries=llm.max_retries,
        )
    msg = f"Unsupported LLM provider: {llm.provider}"
    raise ValueError(msg)


def build_extraction_client(settings: AppSettings | None = None) -> LLMClient:
    resolved = settings or load_settings()
    if resolved.llm.provider == "fake":
        return FakeLLMClient({})
    return build_structured_llm_client(resolved)


def build_embedding_client(settings: AppSettings | None = None) -> EmbeddingClient:
    resolved = settings or load_settings()
    if resolved.embedding.provider == "fake":
        return FakeEmbeddingClient()
    return SentenceTransformerEmbeddingClient(model_name=resolved.embedding.model)


def build_vector_client(
    *,
    embedding_client: EmbeddingClient,
    settings: AppSettings | None = None,
) -> VectorIndexClient:
    resolved = settings or load_settings()
    if resolved.embedding.provider == "fake":
        return FakeVectorClient()
    dimensions = getattr(embedding_client, "dimensions", None)
    if not isinstance(dimensions, int):
        msg = "Embedding client must expose integer dimensions for Qdrant"
        raise ValueError(msg)
    return QdrantVectorClient.from_url(resolved.services.qdrant_url, dimensions=dimensions)


def build_search_client(
    settings: AppSettings | None = None,
) -> FakeOpenSearchClient | OpenSearchClient:
    resolved = settings or load_settings()
    if resolved.llm.provider == "fake" and resolved.embedding.provider == "fake":
        return FakeOpenSearchClient()
    return OpenSearchClient.from_url(resolved.services.opensearch_url)


def build_object_store(settings: AppSettings | None = None) -> ObjectStore:
    resolved = settings or load_settings()
    if resolved.storage.object_store == "local":
        return LocalStore(Path(resolved.storage.local_root))
    if resolved.storage.object_store == "minio":
        return MinioStore(
            endpoint=resolved.services.minio_endpoint,
            access_key=_require_setting(
                "EBRAG_STORAGE__MINIO_ACCESS_KEY", resolved.storage.minio_access_key
            ),
            secret_key=_require_setting(
                "EBRAG_STORAGE__MINIO_SECRET_KEY", resolved.storage.minio_secret_key
            ),
            secure=resolved.storage.minio_secure,
        )
    msg = "S3 object store is not implemented in the single-node runtime"
    raise NotImplementedError(msg)


def build_indexers(
    session: Session,
    settings: AppSettings | None = None,
) -> tuple[OpenSearchIndexer, VectorIndexer, GraphIndexer]:
    resolved = settings or load_settings()
    embedding_client = build_embedding_client(resolved)
    vector_client = build_vector_client(embedding_client=embedding_client, settings=resolved)
    search_client = build_search_client(resolved)
    return (
        OpenSearchIndexer(search_client),
        VectorIndexer(
            vector_client,
            embedding_client,
            collection_name=resolved.vector.collection,
        ),
        GraphIndexer(session),
    )


def build_retrieval_components(
    session: Session,
    settings: AppSettings | None = None,
) -> tuple[StructuredRetriever, LexicalRetriever, VectorRetriever, GraphRetriever, FakeReranker]:
    resolved = settings or load_settings()
    embedding_client = build_embedding_client(resolved)
    vector_client = build_vector_client(embedding_client=embedding_client, settings=resolved)
    search_client = build_search_client(resolved)
    return (
        StructuredRetriever(session),
        LexicalRetriever(search_client),
        VectorRetriever(
            vector_client,
            embedding_client,
            collection_name=resolved.vector.collection,
        ),
        GraphRetriever(session),
        FakeReranker(),
    )
