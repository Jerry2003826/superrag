from __future__ import annotations

from ebrag.reporting.evidence_tables import evidence_table_csv
from ebrag.reporting.export import export_review_bundle
from ebrag.reporting.grade import GradeAssessment
from ebrag.reporting.prisma import PrismCounts
from ebrag.reporting.rob import RiskOfBiasAssessment
from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.extraction import ResultNode


def _result() -> ResultNode:
    return ResultNode.model_validate(
        {
            "result_id": "R00000001",
            "study_id": "S00000001",
            "paper_id": "P00000001",
            "study_type": "animal",
            "intervention": "Compound X",
            "outcome": "IL-6",
            "direction": "decreased",
            "scope": "animal",
            "evidence_span_id": "E00000001",
        }
    )


def _span() -> EvidenceSpan:
    return EvidenceSpan(
        evidence_span_id="E00000001",
        paper_id="P00000001",
        study_id="S00000001",
        source_format="JATS_XML",
        parser_name="jats",
        section="Results",
        page=4,
        text="Compound X reduced IL-6.",
    )


def test_evidence_table_csv_contains_traceability_columns() -> None:
    csv_text = evidence_table_csv(results=[_result()], evidence_spans=[_span()])

    assert "result_id,paper_id,study_id,evidence_span_id" in csv_text
    assert "E00000001" in csv_text
    assert "Results" in csv_text


def test_export_review_bundle_contains_required_reports() -> None:
    bundle = export_review_bundle(
        prisma_counts=PrismCounts(
            title_abstract_screened=3,
            title_abstract_included=2,
            title_abstract_excluded=1,
            title_abstract_uncertain=0,
            full_text_screened=2,
            full_text_included=1,
            full_text_excluded=1,
            full_text_uncertain=0,
        ),
        results=[_result()],
        evidence_spans=[_span()],
        rob_assessments=[
            RiskOfBiasAssessment(
                study_id="S00000001",
                randomization="some_concerns",
                blinding="some_concerns",
                incomplete_outcome_data="low",
                overall="some_concerns",
                rationale="Fixture assessment.",
            )
        ],
        grade_assessments=[
            GradeAssessment(outcome="IL-6", certainty="low", rationale="Animal evidence only.")
        ],
        audit_events=[
            {"action": "paper.create", "target_type": "paper", "target_id": "P00000001"}
        ],
    )

    assert set(bundle) == {
        "prisma.md",
        "evidence_table.csv",
        "risk_of_bias.md",
        "grade.md",
        "audit.md",
    }
    assert "PRISMA" in bundle["prisma.md"]
    assert "Risk of Bias" in bundle["risk_of_bias.md"]
