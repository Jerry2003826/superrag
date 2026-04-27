from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ebrag.schemas.ids import StableId
from ebrag.schemas.retrieval import EvidencePack
from ebrag.synthesis.prompt_builder import build_synthesis_prompt


class SynthesisSentence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    cited_result_ids: list[StableId]
    cited_evidence_span_ids: list[StableId]


class SynthesisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer_id: str = Field(min_length=1)
    abstained: bool = False
    sentences: list[SynthesisSentence] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class SynthesisClient(Protocol):
    def synthesize_json(self, *, prompt: str, evidence_pack: EvidencePack) -> dict[str, Any]:
        """Return structured synthesis JSON."""


class FakeSynthesisClient:
    def synthesize_json(self, *, prompt: str, evidence_pack: EvidencePack) -> dict[str, Any]:
        _ = prompt
        if evidence_pack.sufficiency == "insufficient":
            return {
                "answer_id": "answer-1",
                "abstained": True,
                "sentences": [],
                "reasons": [evidence_pack.sufficiency_reason],
            }
        if not evidence_pack.eligible_results:
            return {
                "answer_id": "answer-1",
                "abstained": True,
                "sentences": [],
                "reasons": ["no eligible results"],
            }
        first = evidence_pack.eligible_results[0]
        return {
            "answer_id": "answer-1",
            "abstained": False,
            "sentences": [
                {
                    "text": (
                        f"{first.intervention or 'The intervention'} showed a "
                        f"{first.direction} effect on {first.outcome} in {first.scope} evidence."
                    ),
                    "cited_result_ids": [first.result_id],
                    "cited_evidence_span_ids": [first.evidence_span_id],
                }
            ],
            "reasons": [],
        }


class Synthesizer:
    def __init__(self, client: SynthesisClient) -> None:
        self.client = client

    def synthesize(self, evidence_pack: EvidencePack) -> SynthesisOutput:
        prompt = build_synthesis_prompt(evidence_pack)
        return SynthesisOutput.model_validate(
            self.client.synthesize_json(prompt=prompt, evidence_pack=evidence_pack)
        )
