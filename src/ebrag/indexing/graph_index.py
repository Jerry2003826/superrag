from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.db.repositories import generate_stable_id


def _get_or_create_node(
    session: Session,
    *,
    node_type: str,
    stable_key: str,
    label: str,
    properties: dict[str, Any] | None = None,
) -> models.GraphNode:
    node = session.scalar(
        select(models.GraphNode).where(
            models.GraphNode.node_type == node_type,
            models.GraphNode.stable_key == stable_key,
        )
    )
    if node is not None:
        return node
    node = models.GraphNode(
        node_id=generate_stable_id(session, models.GraphNode),
        node_type=node_type,
        stable_key=stable_key,
        label=label,
        properties=properties or {},
    )
    session.add(node)
    session.flush()
    return node


def _create_edge(
    session: Session,
    *,
    source_node_id: str,
    target_node_id: str,
    edge_type: str,
    evidence_span_id: str | None = None,
    properties: dict[str, Any] | None = None,
) -> models.GraphEdge:
    edge = models.GraphEdge(
        edge_id=generate_stable_id(session, models.GraphEdge),
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        edge_type=edge_type,
        properties=properties or {},
        evidence_span_id=evidence_span_id,
        confidence=1.0,
    )
    session.add(edge)
    session.flush()
    return edge


@dataclass(frozen=True)
class GraphIndexer:
    session: Session

    def index_result(self, result: models.Result) -> models.GraphEdge:
        study_node = _get_or_create_node(
            self.session,
            node_type="study",
            stable_key=result.study_id,
            label=result.study_id,
        )
        result_node = _get_or_create_node(
            self.session,
            node_type="result",
            stable_key=result.result_id,
            label=result.outcome,
            properties={
                "paper_id": result.paper_id,
                "scope": result.scope,
                "direction": result.direction,
            },
        )
        evidence_node = _get_or_create_node(
            self.session,
            node_type="evidence_span",
            stable_key=result.evidence_span_id,
            label=result.evidence_span_id,
        )
        _create_edge(
            self.session,
            source_node_id=study_node.node_id,
            target_node_id=result_node.node_id,
            edge_type="HAS_RESULT",
        )
        return _create_edge(
            self.session,
            source_node_id=result_node.node_id,
            target_node_id=evidence_node.node_id,
            edge_type="SUPPORTED_BY",
            evidence_span_id=result.evidence_span_id,
            properties={"result_id": result.result_id},
        )
