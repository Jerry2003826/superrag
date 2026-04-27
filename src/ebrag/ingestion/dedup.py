from __future__ import annotations

import re
import string


def normalize_title(title: str) -> str:
    table = str.maketrans("", "", string.punctuation)
    without_punctuation = title.translate(table)
    return re.sub(r"\s+", " ", without_punctuation).strip().lower()


def normalize_doi(doi: str | None) -> str | None:
    if doi is None:
        return None
    normalized = doi.strip().lower()
    if not normalized:
        return None
    return normalized.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
