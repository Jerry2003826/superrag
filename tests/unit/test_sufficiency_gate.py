from __future__ import annotations

from ebrag.retrieval.sufficiency_gate import apply_sufficiency, assess_sufficiency
from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.extraction import ResultNode
from ebrag.schemas.retrieval import EvidencePack


def _result(
    *,
    result_id: str = "R00000001",
    direction: str = "decreased",
    scope: str = "animal",
) -> ResultNode:
    return ResultNode.model_validate(
        {
            "result_id": result_id,
            "study_id": "S00000001",
            "paper_id": "P00000001",
            "study_type": "animal",
            "intervention": "Compound X",
            "outcome": "IL-6",
            "direction": direction,
            "scope": scope,
            "evidence_span_id": "E00000001",
            "extraction_status": "verified",
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
        text="Compound X reduced IL-6.",
    )


def _pack(
    *,
    results: list[ResultNode] | None = None,
    evidence: list[EvidenceSpan] | None = None,
    excluded: list[dict[str, str]] | None = None,
) -> EvidencePack:
    return EvidencePack(
        query="Does compound X reduce IL-6?",
        route=["structured"],
        eligible_results=results if results is not None else [_result()],
        supporting_evidence=evidence if evidence is not None else [_span()],
        excluded_results=excluded or [],
        sufficiency="partial",
        sufficiency_reason="unchecked",
    )


def test_sufficiency_requires_results_and_evidence() -> None:
    assert assess_sufficiency(_pack(results=[])).sufficiency == "insufficient"
    assert assess_sufficiency(_pack(evidence=[])).sufficiency == "insufficient"


def test_sufficiency_marks_all_wrong_scope_insufficient() -> None:
    verdict = assess_sufficiency(
        _pack(excluded=[{"reason_code": "wrong_scope"}, {"reason_code": "wrong_scope"}])
    )

    assert verdict.sufficiency == "insufficient"


def test_sufficiency_marks_conflicts_partial() -> None:
    verdict = assess_sufficiency(
        _pack(
            results=[
                _result(result_id="R00000001", direction="decreased"),
                _result(result_id="R00000002", direction="no_significant_difference"),
            ]
        )
    )

    assert verdict.sufficiency == "partial"
    assert verdict.include_uncertainty_and_conflicts


def test_human_clinical_question_with_animal_evidence_is_partial() -> None:
    verdict = assess_sufficiency(_pack(), query_scope="human_clinical")

    assert verdict.sufficiency == "partial"


def test_sufficient_pack_can_be_applied() -> None:
    verdict = assess_sufficiency(_pack())
    updated = apply_sufficiency(_pack(), verdict)

    assert updated.sufficiency == "sufficient"
    assert updated.sufficiency_reason == "scope matched with supporting evidence"
