from __future__ import annotations

from dataclasses import dataclass

from ebrag.db import models
from ebrag.indexing.graph_index import GraphIndexer
from ebrag.indexing.opensearch_index import OpenSearchIndexer
from ebrag.indexing.vector_index import VectorIndexer


@dataclass(frozen=True)
class IndexBuildResult:
    lexical_documents: int
    vector_points: int
    graph_edges: int


def build_indexes(
    *,
    chunks: list[models.Chunk],
    evidence_spans: list[models.EvidenceSpan],
    results: list[models.Result],
    opensearch_indexer: OpenSearchIndexer,
    vector_indexer: VectorIndexer,
    graph_indexer: GraphIndexer,
) -> IndexBuildResult:
    lexical_count = 0
    for chunk in chunks:
        opensearch_indexer.index_chunk(chunk)
        lexical_count += 1
    for span in evidence_spans:
        opensearch_indexer.index_evidence_span(span)
        vector_indexer.index_evidence_span(span)
        lexical_count += 1
    graph_count = 0
    for result in results:
        graph_indexer.index_result(result)
        graph_count += 2
    return IndexBuildResult(
        lexical_documents=lexical_count,
        vector_points=len(evidence_spans),
        graph_edges=graph_count,
    )
