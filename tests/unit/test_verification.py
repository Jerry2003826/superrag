from __future__ import annotations

from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.extraction import ResultNode
from ebrag.schemas.retrieval import EvidencePack
from ebrag.schemas.synthesis import AtomicClaim
from ebrag.schemas.verification import VerificationVerdict
from ebrag.verification.deterministic import verify_citation_ids
from ebrag.verification.final_gate import run_final_gate
from ebrag.verification.numeric_verifier import verify_numeric_claim


def _pack() -> EvidencePack:
    return EvidencePack(
        query="Does compound X reduce IL-6?",
        route=["structured"],
        eligible_results=[
            ResultNode.model_validate(
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
                    "extraction_status": "verified",
                }
            )
        ],
        supporting_evidence=[
            EvidenceSpan(
                evidence_span_id="E00000001",
                paper_id="P00000001",
                study_id="S00000001",
                source_format="JATS_XML",
                parser_name="jats",
                section="Results",
                text="Compound X reduced IL-6 by 32% with p=0.01.",
            )
        ],
        sufficiency="sufficient",
        sufficiency_reason="scope matched",
    )


def test_deterministic_checker_rejects_unknown_citation_ids() -> None:
    claim = AtomicClaim(
        claim_id="CLM00000001",
        text="Compound X reduced IL-6.",
        cited_result_ids=["R99999999"],
        cited_evidence_span_ids=["E00000001"],
        claim_type="fact",
    )

    verdict = verify_citation_ids(claim, _pack())

    assert verdict.verdict == "unsupported"


def test_numeric_verifier_rejects_uncited_numeric_claim() -> None:
    claim = AtomicClaim(
        claim_id="CLM00000001",
        text="Compound X reduced IL-6 by 99%.",
        cited_result_ids=["R00000001"],
        cited_evidence_span_ids=["E00000001"],
        claim_type="numeric",
    )

    verdict = verify_numeric_claim(claim, _pack())

    assert verdict.verdict == "uncited_numeric"
    assert verdict.requires_human_review


def test_final_gate_blocks_unsupported_wrong_scope_and_uncited_numeric() -> None:
    result = run_final_gate(
        [
            VerificationVerdict(
                claim_id="CLM00000001",
                verdict="supported",
                reason="ok",
            ),
            VerificationVerdict(
                claim_id="CLM00000002",
                verdict="wrong_scope",
                reason="animal evidence used for human claim",
            ),
            VerificationVerdict(
                claim_id="CLM00000003",
                verdict="uncited_numeric",
                reason="99 not cited",
            ),
        ]
    )

    assert result.blocked
    assert result.abstained
    assert len(result.reasons) == 2
