from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.retrieval.graph_retriever import GraphRetriever
from ebrag.retrieval.lexical_retriever import LexicalRetriever
from ebrag.retrieval.query_router import route_query
from ebrag.retrieval.reranker import FakeReranker
from ebrag.retrieval.structured_retriever import StructuredRetriever
from ebrag.retrieval.vector_retriever import VectorRetriever
from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.extraction import ResultNode
from ebrag.schemas.retrieval import EvidencePack


def result_to_node(result: models.Result) -> ResultNode:
    return ResultNode.model_validate(
        {
            "result_id": result.result_id,
            "study_id": result.study_id,
            "paper_id": result.paper_id,
            "study_type": result.study_type,
            "population_or_model": result.population_or_model,
            "species": result.species,
            "cell_line": result.cell_line,
            "intervention": result.intervention,
            "comparator": result.comparator,
            "outcome": result.outcome,
            "assay": result.assay,
            "direction": result.direction or "unclear",
            "effect_size": result.effect_size,
            "p_value": result.p_value,
            "confidence_interval": result.confidence_interval,
            "sample_size": result.sample_size,
            "dose": result.dose,
            "duration": result.duration,
            "unit": result.unit,
            "scope": result.scope,
            "evidence_span_id": result.evidence_span_id,
            "extraction_status": result.extraction_status,
        }
    )


def span_to_schema(span: models.EvidenceSpan) -> EvidenceSpan:
    return EvidenceSpan.model_validate(
        {
            "evidence_span_id": span.evidence_span_id,
            "paper_id": span.paper_id,
            "study_id": span.study_id,
            "source_format": span.source_format,
            "parser_name": span.parser_name,
            "parser_version": span.parser_version,
            "section": span.section,
            "page": span.page,
            "paragraph": span.paragraph,
            "figure_or_table": span.figure_or_table,
            "table_row": span.table_row,
            "table_column": span.table_column,
            "bbox": span.bbox,
            "char_start": span.char_start,
            "char_end": span.char_end,
            "text": span.text,
            "parse_confidence": span.parse_confidence,
            "source_hash": span.source_hash,
        }
    )


def _has_direction_conflict(results: list[models.Result]) -> bool:
    positive = {"increased", "decreased"}
    negative = {"no_significant_difference", "mixed"}
    directions = {result.direction for result in results}
    return bool(directions & positive) and bool(directions & negative)


@dataclass(frozen=True)
class EvidencePackBuilder:
    session: Session
    structured_retriever: StructuredRetriever
    lexical_retriever: LexicalRetriever
    vector_retriever: VectorRetriever
    graph_retriever: GraphRetriever
    reranker: FakeReranker

    def build(self, query: str, *, limit: int = 30) -> EvidencePack:
        routes = route_query(query)
        result_by_id: dict[str, models.Result] = {}
        evidence_span_ids: set[str] = set()

        if "structured" in routes:
            for result in self.structured_retriever.search(query, limit=limit):
                result_by_id[result.result_id] = result
                evidence_span_ids.add(result.evidence_span_id)
        if "graph" in routes:
            for result in self.graph_retriever.search(query, limit=limit):
                result_by_id[result.result_id] = result
                evidence_span_ids.add(result.evidence_span_id)
        if "lexical" in routes:
            for payload in self.lexical_retriever.search(query, limit=limit):
                evidence_id = payload.get("evidence_span_id")
                if isinstance(evidence_id, str):
                    evidence_span_ids.add(evidence_id)
        if "vector" in routes:
            for point in self.vector_retriever.search(query, limit=limit):
                payload = point.get("payload", {})
                evidence_id = payload.get("evidence_span_id") if isinstance(payload, dict) else None
                if isinstance(evidence_id, str):
                    evidence_span_ids.add(evidence_id)

        if evidence_span_ids:
            linked_results = self.session.scalars(
                select(models.Result).where(models.Result.evidence_span_id.in_(evidence_span_ids))
            )
            for result in linked_results:
                result_by_id[result.result_id] = result

        reranked = self.reranker.rerank_results(
            query=query,
            results=list(result_by_id.values()),
            limit=limit,
        )
        evidence = [
            result.evidence_span
            for result in reranked
            if result.evidence_span is not None
        ]
        unique_evidence = list({span.evidence_span_id: span for span in evidence}.values())
        conflicts = reranked if _has_direction_conflict(reranked) else []
        return EvidencePack(
            query=query,
            route=routes,
            eligible_results=[result_to_node(result) for result in reranked],
            supporting_evidence=[span_to_schema(span) for span in unique_evidence],
            conflicting_results=[result_to_node(result) for result in conflicts],
            excluded_results=[],
            sufficiency="sufficient" if reranked and unique_evidence else "insufficient",
            sufficiency_reason="retrieved evidence" if reranked else "no eligible results",
        )
