from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ebrag.schemas.ids import StableId
from ebrag.schemas.screening import ScreeningDecision


@dataclass(frozen=True)
class TitleAbstractScreeningBaseline:
    include_keywords: tuple[str, ...]
    exclude_keywords: tuple[str, ...] = ()
    uncertain_threshold: float = 0.35

    def screen(
        self,
        *,
        paper_id: StableId,
        title: str,
        abstract: str | None,
        study_id: StableId | None = None,
    ) -> ScreeningDecision:
        text = f"{title} {abstract or ''}".lower()
        include_hits = [keyword for keyword in self.include_keywords if keyword.lower() in text]
        exclude_hits = [keyword for keyword in self.exclude_keywords if keyword.lower() in text]

        if exclude_hits:
            return ScreeningDecision(
                paper_id=paper_id,
                study_id=study_id,
                level="title_abstract",
                decision="exclude",
                reason_code="exclude_keyword",
                reason_text=", ".join(exclude_hits),
                reviewer_type="rule_based",
                confidence=0.9,
            )
        confidence = min(1.0, len(include_hits) / max(1, len(self.include_keywords)))
        if confidence >= self.uncertain_threshold:
            decision: Literal["include", "uncertain"] = "include"
            reason_code = "include_keyword"
            reason_text = ", ".join(include_hits)
        else:
            decision = "uncertain"
            reason_code = "low_keyword_overlap"
            reason_text = "Insufficient title/abstract keyword overlap"
        return ScreeningDecision(
            paper_id=paper_id,
            study_id=study_id,
            level="title_abstract",
            decision=decision,
            reason_code=reason_code,
            reason_text=reason_text,
            reviewer_type="rule_based",
            confidence=confidence,
        )
