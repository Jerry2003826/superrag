from __future__ import annotations

from sqlalchemy.orm import Session

from ebrag.db.repositories import (
    EvidenceRepository,
    PaperRepository,
    ResultRepository,
    StudyRepository,
)
from ebrag.indexing.build_indexes import build_indexes
from ebrag.indexing.graph_index import GraphIndexer
from ebrag.indexing.opensearch_index import FakeOpenSearchClient, OpenSearchIndexer
from ebrag.indexing.vector_index import FakeEmbeddingClient, FakeVectorClient, VectorIndexer
from ebrag.ingestion.dedup import normalize_title
from ebrag.retrieval.evidence_pack import EvidencePackBuilder
from ebrag.retrieval.graph_retriever import GraphRetriever
from ebrag.retrieval.lexical_retriever import LexicalRetriever
from ebrag.retrieval.query_router import route_query
from ebrag.retrieval.reranker import FakeReranker
from ebrag.retrieval.structured_retriever import StructuredRetriever
from ebrag.retrieval.vector_retriever import VectorRetriever


def test_query_router_selects_expected_routes() -> None:
    routes = route_query("Does compound X reduce IL-6 in animal studies?")

    assert routes == ["structured", "lexical", "vector", "graph"]


def test_retrieval_pipeline_builds_traceable_evidence_pack(db_session: Session) -> None:
    paper = PaperRepository(db_session).create(
        title="Compound X retrieval study",
        normalized_title=normalize_title("Compound X retrieval study"),
    )
    study = StudyRepository(db_session).create()
    span = EvidenceRepository(db_session).create_span(
        paper_id=paper.paper_id,
        study_id=study.study_id,
        source_format="JATS_XML",
        section="Results",
        page=5,
        text="Compound X reduced IL-6 in AD mouse models.",
    )
    result = ResultRepository(db_session).create(
        study_id=study.study_id,
        paper_id=paper.paper_id,
        evidence_span_id=span.evidence_span_id,
        study_type="animal",
        population_or_model="AD mouse model",
        species="mouse",
        intervention="Compound X",
        outcome="IL-6",
        direction="decreased",
        scope="animal",
        extraction_status="verified",
    )
    search_client = FakeOpenSearchClient()
    vector_client = FakeVectorClient()
    embedding_client = FakeEmbeddingClient()
    build_indexes(
        chunks=[],
        evidence_spans=[span],
        results=[result],
        opensearch_indexer=OpenSearchIndexer(search_client),
        vector_indexer=VectorIndexer(vector_client, embedding_client),
        graph_indexer=GraphIndexer(db_session),
    )

    pack = EvidencePackBuilder(
        session=db_session,
        structured_retriever=StructuredRetriever(db_session),
        lexical_retriever=LexicalRetriever(search_client),
        vector_retriever=VectorRetriever(vector_client, embedding_client),
        graph_retriever=GraphRetriever(db_session),
        reranker=FakeReranker(),
    ).build("Does compound X reduce IL-6 in animal studies?")

    assert pack.sufficiency == "sufficient"
    assert pack.eligible_results[0].result_id == result.result_id
    assert pack.supporting_evidence[0].evidence_span_id == span.evidence_span_id
    assert pack.supporting_evidence[0].page == 5
    assert "graph" in pack.route
