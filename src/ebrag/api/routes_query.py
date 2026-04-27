from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ebrag.db.session import get_session
from ebrag.extraction.llm_client import StructuredJSONClient
from ebrag.providers import build_retrieval_components, build_structured_llm_client
from ebrag.retrieval.evidence_pack import EvidencePackBuilder
from ebrag.retrieval.sufficiency_gate import apply_sufficiency, assess_sufficiency
from ebrag.schemas.retrieval import EvidencePack
from ebrag.settings import load_settings
from ebrag.synthesis.atomic_claims import claims_from_synthesis
from ebrag.synthesis.synthesizer import FakeSynthesisClient, Synthesizer
from ebrag.verification.deterministic import verify_claims_deterministically
from ebrag.verification.final_gate import run_final_gate
from ebrag.verification.llm_verifier import StructuredLLMVerifier
from ebrag.verification.numeric_verifier import verify_numeric_claims

router = APIRouter(prefix="/query", tags=["query"])
SessionDep = Annotated[Session, Depends(get_session)]


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    query_scope: Literal["human_clinical", "animal", "in_vitro", "any"] = "any"


def _build_evidence_pack(session: Session, query: str) -> EvidencePack:
    structured, lexical, vector, graph, reranker = build_retrieval_components(session)
    return EvidencePackBuilder(
        session=session,
        structured_retriever=structured,
        lexical_retriever=lexical,
        vector_retriever=vector,
        graph_retriever=graph,
        reranker=reranker,
    ).build(query)


def _build_synthesis_client() -> FakeSynthesisClient | StructuredJSONClient:
    settings = load_settings()
    if settings.llm.provider == "fake":
        return FakeSynthesisClient()
    return build_structured_llm_client(settings)


@router.post("/evidence-pack", response_model=EvidencePack)
def evidence_pack(
    request: QueryRequest,
    session: SessionDep,
) -> EvidencePack:
    return _build_evidence_pack(session, request.query)


@router.post("/full")
def full_query(
    request: QueryRequest,
    session: SessionDep,
) -> dict[str, Any]:
    pack = _build_evidence_pack(session, request.query)
    verdict = assess_sufficiency(pack, query_scope=request.query_scope)
    pack = apply_sufficiency(pack, verdict)
    synthesis = Synthesizer(_build_synthesis_client()).synthesize(pack)
    claims = claims_from_synthesis(synthesis)
    verification = (
        verify_claims_deterministically(claims, pack) + verify_numeric_claims(claims, pack)
    )
    settings = load_settings()
    if settings.llm.provider != "fake":
        evidence_text = "\n".join(span.text for span in pack.supporting_evidence)
        verifier = StructuredLLMVerifier(build_structured_llm_client(settings))
        verification.extend(verifier.verify(claim, evidence_text) for claim in claims)
    final = run_final_gate(verification)
    return {
        "abstained": synthesis.abstained or final.abstained,
        "block_reasons": list(final.reasons),
        "sufficiency": pack.sufficiency,
        "sufficiency_reason": pack.sufficiency_reason,
        "answer": synthesis.model_dump(),
        "claims": [claim.model_dump() for claim in claims],
        "verification": [verdict.model_dump() for verdict in verification],
    }
