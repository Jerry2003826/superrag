from __future__ import annotations

from dataclasses import dataclass

from ebrag.schemas.screening import ScreeningDecision


@dataclass(frozen=True)
class PrismCounts:
    title_abstract_screened: int
    title_abstract_included: int
    title_abstract_excluded: int
    title_abstract_uncertain: int
    full_text_screened: int
    full_text_included: int
    full_text_excluded: int
    full_text_uncertain: int


def build_prisma_counts(decisions: list[ScreeningDecision]) -> PrismCounts:
    title_abstract = [decision for decision in decisions if decision.level == "title_abstract"]
    full_text = [decision for decision in decisions if decision.level == "full_text"]

    def count(items: list[ScreeningDecision], outcome: str) -> int:
        return sum(1 for item in items if item.decision == outcome)

    return PrismCounts(
        title_abstract_screened=len(title_abstract),
        title_abstract_included=count(title_abstract, "include"),
        title_abstract_excluded=count(title_abstract, "exclude"),
        title_abstract_uncertain=count(title_abstract, "uncertain"),
        full_text_screened=len(full_text),
        full_text_included=count(full_text, "include"),
        full_text_excluded=count(full_text, "exclude"),
        full_text_uncertain=count(full_text, "uncertain"),
    )
