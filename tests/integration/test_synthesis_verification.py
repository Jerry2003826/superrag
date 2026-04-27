from __future__ import annotations

from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.extraction import ResultNode
from ebrag.schemas.retrieval import EvidencePack
from ebrag.synthesis.atomic_claims import claims_from_synthesis
from ebrag.synthesis.synthesizer import FakeSynthesisClient, Synthesizer
from ebrag.verification.deterministic import verify_claims_deterministically
from ebrag.verification.final_gate import run_final_gate
from ebrag.verification.numeric_verifier import verify_numeric_claims


def test_synthesis_to_verification_final_gate_allows_supported_claim() -> None:
    pack = EvidencePack(
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
                text="Compound X reduced IL-6 in mice.",
            )
        ],
        sufficiency="sufficient",
        sufficiency_reason="scope matched",
    )

    synthesis = Synthesizer(FakeSynthesisClient()).synthesize(pack)
    claims = claims_from_synthesis(synthesis)
    verdicts = verify_claims_deterministically(claims, pack) + verify_numeric_claims(claims, pack)
    final = run_final_gate(verdicts)

    assert not final.blocked
    assert not final.abstained
