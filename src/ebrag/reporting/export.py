from __future__ import annotations

from ebrag.reporting.evidence_tables import evidence_table_csv
from ebrag.reporting.grade import GradeAssessment, grade_markdown
from ebrag.reporting.prisma import PrismCounts
from ebrag.reporting.rob import RiskOfBiasAssessment, rob_markdown
from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.extraction import ResultNode


def audit_report_markdown(audit_events: list[dict[str, str]]) -> str:
    lines = ["# Audit Report", ""]
    for event in audit_events:
        lines.append(
            f"- {event.get('action', '')}: {event.get('target_type', '')}/"
            f"{event.get('target_id', '')}"
        )
    return "\n".join(lines) + "\n"


def prisma_markdown(counts: PrismCounts) -> str:
    return (
        "# PRISMA Counts\n\n"
        f"- Title/abstract screened: {counts.title_abstract_screened}\n"
        f"- Title/abstract included: {counts.title_abstract_included}\n"
        f"- Title/abstract excluded: {counts.title_abstract_excluded}\n"
        f"- Full text screened: {counts.full_text_screened}\n"
        f"- Full text included: {counts.full_text_included}\n"
        f"- Full text excluded: {counts.full_text_excluded}\n"
    )


def export_review_bundle(
    *,
    prisma_counts: PrismCounts,
    results: list[ResultNode],
    evidence_spans: list[EvidenceSpan],
    rob_assessments: list[RiskOfBiasAssessment],
    grade_assessments: list[GradeAssessment],
    audit_events: list[dict[str, str]],
) -> dict[str, str]:
    return {
        "prisma.md": prisma_markdown(prisma_counts),
        "evidence_table.csv": evidence_table_csv(results=results, evidence_spans=evidence_spans),
        "risk_of_bias.md": rob_markdown(rob_assessments),
        "grade.md": grade_markdown(grade_assessments),
        "audit.md": audit_report_markdown(audit_events),
    }
