from __future__ import annotations

from typing import Any

from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.extraction import ResultNode
from ebrag.schemas.retrieval import EvidencePack
from ebrag.synthesis.atomic_claims import claims_from_synthesis
from ebrag.synthesis.prompt_builder import build_synthesis_prompt
from ebrag.synthesis.scope_guard import is_scope_overreach
from ebrag.synthesis.synthesizer import FakeSynthesisClient, Synthesizer


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
                text="Compound X reduced IL-6 in mice.",
            )
        ],
        sufficiency="sufficient",
        sufficiency_reason="scope matched",
    )


def test_synthesis_prompt_uses_evidence_pack_identifiers() -> None:
    prompt = build_synthesis_prompt(_pack())

    assert "result_id=R00000001" in prompt
    assert "E00000001" in prompt
    assert "raw chunks" not in prompt.lower()


def test_synthesizer_and_atomic_claims_keep_sentence_citations() -> None:
    output = Synthesizer(FakeSynthesisClient()).synthesize(_pack())
    claims = claims_from_synthesis(output)

    assert not output.abstained
    assert claims[0].cited_result_ids == ["R00000001"]
    assert claims[0].cited_evidence_span_ids == ["E00000001"]


def test_synthesizer_abstains_when_insufficient() -> None:
    pack = _pack().model_copy(update={"sufficiency": "insufficient", "sufficiency_reason": "none"})
    output = Synthesizer(FakeSynthesisClient()).synthesize(pack)

    assert output.abstained
    assert output.reasons == ["none"]


def test_synthesizer_accepts_nested_provider_synthesis_payload() -> None:
    class NestedClient:
        def synthesize_json(self, *, prompt: str, evidence_pack: EvidencePack) -> dict[str, Any]:
            _ = prompt, evidence_pack
            return {
                "synthesis": {
                    "sentences": [
                        {
                            "content": "Compound X reduced IL-6 in animal evidence.",
                            "cited_result_ids": ["R00000001"],
                            "cited_evidence_span_ids": ["E00000001"],
                        }
                    ]
                }
            }

    output = Synthesizer(NestedClient()).synthesize(_pack())

    assert output.answer_id == "answer-1"
    assert output.sentences[0].text == "Compound X reduced IL-6 in animal evidence."
    assert output.sentences[0].cited_evidence_span_ids == ["E00000001"]


def test_scope_guard_blocks_overreach() -> None:
    result = _pack().eligible_results[0]

    assert is_scope_overreach(result=result, requested_scope="human_clinical")
    assert is_scope_overreach(result=result, requested_scope="clinical_efficacy")
    assert not is_scope_overreach(result=result, requested_scope="animal")
