from __future__ import annotations

from dataclasses import dataclass

from ebrag.schemas.verification import VerificationVerdict

BLOCKING_VERDICTS = {
    "unsupported",
    "contradicted",
    "wrong_scope",
    "overgeneralized",
    "uncited_numeric",
}


@dataclass(frozen=True)
class FinalGateResult:
    blocked: bool
    abstained: bool
    reasons: tuple[str, ...]


def run_final_gate(verdicts: list[VerificationVerdict]) -> FinalGateResult:
    blocking = [verdict for verdict in verdicts if verdict.verdict in BLOCKING_VERDICTS]
    if not blocking:
        return FinalGateResult(blocked=False, abstained=False, reasons=())
    return FinalGateResult(
        blocked=True,
        abstained=True,
        reasons=tuple(
            f"{verdict.claim_id}: {verdict.verdict} - {verdict.reason}"
            for verdict in blocking
        ),
    )
