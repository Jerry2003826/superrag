from __future__ import annotations

import re


def route_query(query: str) -> list[str]:
    normalized = query.lower()
    routes: list[str] = []
    if re.search(r"\b(p\s*[<=>]|n\s*=|\d+(?:\.\d+)?\s*(?:mg/kg|%))", normalized):
        routes.append("structured")
    if any(term in normalized for term in ("effect", "reduce", "increase", "outcome", "il-6")):
        routes.extend(["structured", "lexical", "vector"])
    if any(
        term in normalized
        for term in ("study", "studies", "evidence", "relationship", "supported")
    ):
        routes.append("graph")
    if not routes:
        routes = ["lexical", "vector"]
    return list(dict.fromkeys(routes))
