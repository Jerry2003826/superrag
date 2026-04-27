from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from ebrag.db.base import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class Paper(Base):
    __tablename__ = "papers"

    paper_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    doi: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    pmid: Mapped[str | None] = mapped_column(String(64), index=True)
    pmcid: Mapped[str | None] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(Text)
    normalized_title: Mapped[str] = mapped_column(Text, index=True)
    authors: Mapped[list[str]] = mapped_column(JsonType, default=list)
    year: Mapped[int | None] = mapped_column(Integer)
    journal: Mapped[str | None] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text)
    source_database: Mapped[str | None] = mapped_column(String(128))
    source_url: Mapped[str | None] = mapped_column(Text)
    retraction_status: Mapped[str] = mapped_column(String(64), default="unknown")
    erratum_status: Mapped[str] = mapped_column(String(64), default="unknown")
    full_text_available: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )

    reports: Mapped[list[StudyReport]] = relationship(back_populates="paper")
    parsed_documents: Mapped[list[ParsedDocument]] = relationship(back_populates="paper")
    evidence_spans: Mapped[list[EvidenceSpan]] = relationship(back_populates="paper")


class Study(Base, TimestampMixin):
    __tablename__ = "studies"

    study_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    study_design: Mapped[str | None] = mapped_column(Text)
    population_or_model: Mapped[str | None] = mapped_column(Text)
    intervention_or_exposure: Mapped[str | None] = mapped_column(Text)
    comparator: Mapped[str | None] = mapped_column(Text)
    primary_outcomes: Mapped[list[str]] = mapped_column(JsonType, default=list)
    status: Mapped[str] = mapped_column(String(64), default="candidate")

    reports: Mapped[list[StudyReport]] = relationship(back_populates="study")
    evidence_spans: Mapped[list[EvidenceSpan]] = relationship(back_populates="study")


class StudyReport(Base, TimestampMixin):
    __tablename__ = "study_reports"

    report_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    study_id: Mapped[str] = mapped_column(ForeignKey("studies.study_id"), index=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True)
    report_type: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[str | None] = mapped_column(Text)

    study: Mapped[Study] = relationship(back_populates="reports")
    paper: Mapped[Paper] = relationship(back_populates="reports")


class ParsedDocument(Base, TimestampMixin):
    __tablename__ = "parsed_documents"

    parsed_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True)
    source_format: Mapped[str] = mapped_column(String(64))
    parser_name: Mapped[str] = mapped_column(String(128))
    parser_version: Mapped[str | None] = mapped_column(String(64))
    object_uri: Mapped[str] = mapped_column(Text)
    parse_status: Mapped[str] = mapped_column(String(64))
    parse_confidence: Mapped[float | None] = mapped_column(Float)
    qc_status: Mapped[str] = mapped_column(String(64), default="pending")

    paper: Mapped[Paper] = relationship(back_populates="parsed_documents")
    chunks: Mapped[list[Chunk]] = relationship(back_populates="parsed_document")


class Chunk(Base, TimestampMixin):
    __tablename__ = "chunks"

    chunk_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True)
    parsed_id: Mapped[str] = mapped_column(ForeignKey("parsed_documents.parsed_id"), index=True)
    section: Mapped[str | None] = mapped_column(Text, index=True)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    chunk_type: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JsonType, default=dict)

    paper: Mapped[Paper] = relationship()
    parsed_document: Mapped[ParsedDocument] = relationship(back_populates="chunks")
    evidence_spans: Mapped[list[EvidenceSpan]] = relationship(back_populates="chunk")


class EvidenceSpan(Base, TimestampMixin):
    __tablename__ = "evidence_spans"

    evidence_span_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True)
    study_id: Mapped[str | None] = mapped_column(ForeignKey("studies.study_id"), index=True)
    chunk_id: Mapped[str | None] = mapped_column(ForeignKey("chunks.chunk_id"), index=True)
    source_format: Mapped[str] = mapped_column(String(64))
    parser_name: Mapped[str] = mapped_column(String(128))
    parser_version: Mapped[str | None] = mapped_column(String(64))
    section: Mapped[str | None] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)
    paragraph: Mapped[int | None] = mapped_column(Integer)
    figure_or_table: Mapped[str | None] = mapped_column(Text)
    table_row: Mapped[str | None] = mapped_column(Text)
    table_column: Mapped[str | None] = mapped_column(Text)
    bbox: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    parse_confidence: Mapped[float | None] = mapped_column(Float)
    source_hash: Mapped[str | None] = mapped_column(String(128))
    verification_status: Mapped[str] = mapped_column(String(64), default="unverified")

    paper: Mapped[Paper] = relationship(back_populates="evidence_spans")
    study: Mapped[Study | None] = relationship(back_populates="evidence_spans")
    chunk: Mapped[Chunk | None] = relationship(back_populates="evidence_spans")
    results: Mapped[list[Result]] = relationship(back_populates="evidence_span")


class ScreeningDecision(Base, TimestampMixin):
    __tablename__ = "screening_decisions"

    decision_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True)
    study_id: Mapped[str | None] = mapped_column(ForeignKey("studies.study_id"), index=True)
    level: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(64))
    reason_code: Mapped[str | None] = mapped_column(String(128))
    reason_text: Mapped[str | None] = mapped_column(Text)
    evidence_span_id: Mapped[str | None] = mapped_column(
        ForeignKey("evidence_spans.evidence_span_id"), index=True
    )
    reviewer_type: Mapped[str] = mapped_column(String(64))
    reviewer_id: Mapped[str | None] = mapped_column(String(128))
    confidence: Mapped[float | None] = mapped_column(Float)


class Result(Base, TimestampMixin):
    __tablename__ = "results"

    result_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    study_id: Mapped[str] = mapped_column(ForeignKey("studies.study_id"), index=True)
    paper_id: Mapped[str] = mapped_column(ForeignKey("papers.paper_id"), index=True)
    study_type: Mapped[str] = mapped_column(String(128))
    population_or_model: Mapped[str | None] = mapped_column(Text)
    species: Mapped[str | None] = mapped_column(String(128))
    cell_line: Mapped[str | None] = mapped_column(String(128))
    intervention: Mapped[str | None] = mapped_column(Text, index=True)
    comparator: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text, index=True)
    assay: Mapped[str | None] = mapped_column(Text)
    direction: Mapped[str | None] = mapped_column(String(64))
    effect_size: Mapped[str | None] = mapped_column(Text)
    p_value: Mapped[str | None] = mapped_column(String(128))
    confidence_interval: Mapped[str | None] = mapped_column(Text)
    sample_size: Mapped[str | None] = mapped_column(String(128))
    dose: Mapped[str | None] = mapped_column(String(128))
    duration: Mapped[str | None] = mapped_column(String(128))
    unit: Mapped[str | None] = mapped_column(String(128))
    scope: Mapped[str] = mapped_column(String(64), index=True)
    risk_of_bias_overall: Mapped[str | None] = mapped_column(String(64))
    evidence_span_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_spans.evidence_span_id"), index=True
    )
    extraction_status: Mapped[str] = mapped_column(String(64), default="unverified")

    study: Mapped[Study] = relationship()
    paper: Mapped[Paper] = relationship()
    evidence_span: Mapped[EvidenceSpan] = relationship(back_populates="results")


class GraphNode(Base, TimestampMixin):
    __tablename__ = "graph_nodes"
    __table_args__ = (Index("idx_graph_nodes_stable", "node_type", "stable_key", unique=True),)

    node_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    node_type: Mapped[str] = mapped_column(String(64))
    stable_key: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    properties: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)


class GraphEdge(Base, TimestampMixin):
    __tablename__ = "graph_edges"

    edge_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_node_id: Mapped[str] = mapped_column(ForeignKey("graph_nodes.node_id"), index=True)
    target_node_id: Mapped[str] = mapped_column(ForeignKey("graph_nodes.node_id"), index=True)
    edge_type: Mapped[str] = mapped_column(String(64), index=True)
    properties: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    evidence_span_id: Mapped[str | None] = mapped_column(
        ForeignKey("evidence_spans.evidence_span_id"), index=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    source_node: Mapped[GraphNode] = relationship(foreign_keys=[source_node_id])
    target_node: Mapped[GraphNode] = relationship(foreign_keys=[target_node_id])


class Claim(Base, TimestampMixin):
    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    answer_id: Mapped[str] = mapped_column(String(128), index=True)
    claim_text: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str | None] = mapped_column(String(64))
    cited_result_ids: Mapped[list[str]] = mapped_column(JsonType, default=list)
    cited_evidence_span_ids: Mapped[list[str]] = mapped_column(JsonType, default=list)

    verifications: Mapped[list[ClaimVerification]] = relationship(back_populates="claim")


class ClaimVerification(Base, TimestampMixin):
    __tablename__ = "claim_verification"

    verification_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.claim_id"), index=True)
    verdict: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text)
    corrected_claim: Mapped[str | None] = mapped_column(Text)
    verifier_type: Mapped[str] = mapped_column(String(64))
    verifier_version: Mapped[str | None] = mapped_column(String(64))

    claim: Mapped[Claim] = relationship(back_populates="verifications")


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    audit_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    actor_type: Mapped[str] = mapped_column(String(64))
    actor_id: Mapped[str | None] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(128), index=True)
    target_type: Mapped[str] = mapped_column(String(64), index=True)
    target_id: Mapped[str] = mapped_column(String(128), index=True)
    before: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    after: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
