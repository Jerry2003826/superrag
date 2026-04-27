from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "papers",
        sa.Column("paper_id", sa.String(length=32), primary_key=True),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("pmid", sa.String(length=64), nullable=True),
        sa.Column("pmcid", sa.String(length=64), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("authors", json_type, nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("journal", sa.Text(), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("source_database", sa.String(length=128), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("retraction_status", sa.String(length=64), nullable=False),
        sa.Column("erratum_status", sa.String(length=64), nullable=False),
        sa.Column("full_text_available", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_papers_doi", "papers", ["doi"], unique=True)
    op.create_index("ix_papers_normalized_title", "papers", ["normalized_title"])
    op.create_index("ix_papers_pmcid", "papers", ["pmcid"])
    op.create_index("ix_papers_pmid", "papers", ["pmid"])

    op.create_table(
        "studies",
        sa.Column("study_id", sa.String(length=32), primary_key=True),
        sa.Column("study_design", sa.Text(), nullable=True),
        sa.Column("population_or_model", sa.Text(), nullable=True),
        sa.Column("intervention_or_exposure", sa.Text(), nullable=True),
        sa.Column("comparator", sa.Text(), nullable=True),
        sa.Column("primary_outcomes", json_type, nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "study_reports",
        sa.Column("report_id", sa.String(length=32), primary_key=True),
        sa.Column("study_id", sa.String(length=32), sa.ForeignKey("studies.study_id")),
        sa.Column("paper_id", sa.String(length=32), sa.ForeignKey("papers.paper_id")),
        sa.Column("report_type", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_study_reports_paper_id", "study_reports", ["paper_id"])
    op.create_index("ix_study_reports_study_id", "study_reports", ["study_id"])

    op.create_table(
        "parsed_documents",
        sa.Column("parsed_id", sa.String(length=32), primary_key=True),
        sa.Column("paper_id", sa.String(length=32), sa.ForeignKey("papers.paper_id")),
        sa.Column("source_format", sa.String(length=64), nullable=False),
        sa.Column("parser_name", sa.String(length=128), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=True),
        sa.Column("object_uri", sa.Text(), nullable=False),
        sa.Column("parse_status", sa.String(length=64), nullable=False),
        sa.Column("parse_confidence", sa.Float(), nullable=True),
        sa.Column("qc_status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_parsed_documents_paper_id", "parsed_documents", ["paper_id"])

    op.create_table(
        "chunks",
        sa.Column("chunk_id", sa.String(length=32), primary_key=True),
        sa.Column("paper_id", sa.String(length=32), sa.ForeignKey("papers.paper_id")),
        sa.Column("parsed_id", sa.String(length=32), sa.ForeignKey("parsed_documents.parsed_id")),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("chunk_type", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("metadata", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chunks_paper_id", "chunks", ["paper_id"])
    op.create_index("ix_chunks_parsed_id", "chunks", ["parsed_id"])
    op.create_index("ix_chunks_section", "chunks", ["section"])

    op.create_table(
        "evidence_spans",
        sa.Column("evidence_span_id", sa.String(length=32), primary_key=True),
        sa.Column("paper_id", sa.String(length=32), sa.ForeignKey("papers.paper_id")),
        sa.Column(
            "study_id",
            sa.String(length=32),
            sa.ForeignKey("studies.study_id"),
            nullable=True,
        ),
        sa.Column(
            "chunk_id",
            sa.String(length=32),
            sa.ForeignKey("chunks.chunk_id"),
            nullable=True,
        ),
        sa.Column("source_format", sa.String(length=64), nullable=False),
        sa.Column("parser_name", sa.String(length=128), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=True),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("paragraph", sa.Integer(), nullable=True),
        sa.Column("figure_or_table", sa.Text(), nullable=True),
        sa.Column("table_row", sa.Text(), nullable=True),
        sa.Column("table_column", sa.Text(), nullable=True),
        sa.Column("bbox", json_type, nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("parse_confidence", sa.Float(), nullable=True),
        sa.Column("source_hash", sa.String(length=128), nullable=True),
        sa.Column("verification_status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_evidence_spans_chunk_id", "evidence_spans", ["chunk_id"])
    op.create_index("ix_evidence_spans_paper_id", "evidence_spans", ["paper_id"])
    op.create_index("ix_evidence_spans_study_id", "evidence_spans", ["study_id"])

    op.create_table(
        "screening_decisions",
        sa.Column("decision_id", sa.String(length=32), primary_key=True),
        sa.Column("paper_id", sa.String(length=32), sa.ForeignKey("papers.paper_id")),
        sa.Column(
            "study_id",
            sa.String(length=32),
            sa.ForeignKey("studies.study_id"),
            nullable=True,
        ),
        sa.Column(
            "evidence_span_id",
            sa.String(length=32),
            sa.ForeignKey("evidence_spans.evidence_span_id"),
            nullable=True,
        ),
        sa.Column("level", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=True),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("reviewer_type", sa.String(length=64), nullable=False),
        sa.Column("reviewer_id", sa.String(length=128), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_screening_decisions_evidence_span_id",
        "screening_decisions",
        ["evidence_span_id"],
    )
    op.create_index("ix_screening_decisions_paper_id", "screening_decisions", ["paper_id"])
    op.create_index("ix_screening_decisions_study_id", "screening_decisions", ["study_id"])

    op.create_table(
        "results",
        sa.Column("result_id", sa.String(length=32), primary_key=True),
        sa.Column("study_id", sa.String(length=32), sa.ForeignKey("studies.study_id")),
        sa.Column("paper_id", sa.String(length=32), sa.ForeignKey("papers.paper_id")),
        sa.Column(
            "evidence_span_id",
            sa.String(length=32),
            sa.ForeignKey("evidence_spans.evidence_span_id"),
        ),
        sa.Column("study_type", sa.String(length=128), nullable=False),
        sa.Column("population_or_model", sa.Text(), nullable=True),
        sa.Column("species", sa.String(length=128), nullable=True),
        sa.Column("cell_line", sa.String(length=128), nullable=True),
        sa.Column("intervention", sa.Text(), nullable=True),
        sa.Column("comparator", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("assay", sa.Text(), nullable=True),
        sa.Column("direction", sa.String(length=64), nullable=True),
        sa.Column("effect_size", sa.Text(), nullable=True),
        sa.Column("p_value", sa.String(length=128), nullable=True),
        sa.Column("confidence_interval", sa.Text(), nullable=True),
        sa.Column("sample_size", sa.String(length=128), nullable=True),
        sa.Column("dose", sa.String(length=128), nullable=True),
        sa.Column("duration", sa.String(length=128), nullable=True),
        sa.Column("unit", sa.String(length=128), nullable=True),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("risk_of_bias_overall", sa.String(length=64), nullable=True),
        sa.Column("extraction_status", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_results_evidence_span_id", "results", ["evidence_span_id"])
    op.create_index("ix_results_intervention", "results", ["intervention"])
    op.create_index("ix_results_outcome", "results", ["outcome"])
    op.create_index("ix_results_paper_id", "results", ["paper_id"])
    op.create_index("ix_results_scope", "results", ["scope"])
    op.create_index("ix_results_study_id", "results", ["study_id"])

    op.create_table(
        "graph_nodes",
        sa.Column("node_id", sa.String(length=32), primary_key=True),
        sa.Column("node_type", sa.String(length=64), nullable=False),
        sa.Column("stable_key", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("properties", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_graph_nodes_stable",
        "graph_nodes",
        ["node_type", "stable_key"],
        unique=True,
    )

    op.create_table(
        "graph_edges",
        sa.Column("edge_id", sa.String(length=32), primary_key=True),
        sa.Column("source_node_id", sa.String(length=32), sa.ForeignKey("graph_nodes.node_id")),
        sa.Column("target_node_id", sa.String(length=32), sa.ForeignKey("graph_nodes.node_id")),
        sa.Column(
            "evidence_span_id",
            sa.String(length=32),
            sa.ForeignKey("evidence_spans.evidence_span_id"),
            nullable=True,
        ),
        sa.Column("edge_type", sa.String(length=64), nullable=False),
        sa.Column("properties", json_type, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_graph_edges_edge_type", "graph_edges", ["edge_type"])
    op.create_index("ix_graph_edges_evidence_span_id", "graph_edges", ["evidence_span_id"])
    op.create_index("ix_graph_edges_source_node_id", "graph_edges", ["source_node_id"])
    op.create_index("ix_graph_edges_target_node_id", "graph_edges", ["target_node_id"])

    op.create_table(
        "claims",
        sa.Column("claim_id", sa.String(length=32), primary_key=True),
        sa.Column("answer_id", sa.String(length=128), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=64), nullable=True),
        sa.Column("cited_result_ids", json_type, nullable=False),
        sa.Column("cited_evidence_span_ids", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_claims_answer_id", "claims", ["answer_id"])

    op.create_table(
        "claim_verification",
        sa.Column("verification_id", sa.String(length=32), primary_key=True),
        sa.Column("claim_id", sa.String(length=32), sa.ForeignKey("claims.claim_id")),
        sa.Column("verdict", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("corrected_claim", sa.Text(), nullable=True),
        sa.Column("verifier_type", sa.String(length=64), nullable=False),
        sa.Column("verifier_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_claim_verification_claim_id", "claim_verification", ["claim_id"])

    op.create_table(
        "audit_logs",
        sa.Column("audit_id", sa.String(length=32), primary_key=True),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("before", json_type, nullable=True),
        sa.Column("after", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_target_id", "audit_logs", ["target_id"])
    op.create_index("ix_audit_logs_target_type", "audit_logs", ["target_type"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("claim_verification")
    op.drop_table("claims")
    op.drop_table("graph_edges")
    op.drop_table("graph_nodes")
    op.drop_table("results")
    op.drop_table("screening_decisions")
    op.drop_table("evidence_spans")
    op.drop_table("chunks")
    op.drop_table("parsed_documents")
    op.drop_table("study_reports")
    op.drop_table("studies")
    op.drop_table("papers")
