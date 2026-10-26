"""Grounding check: a predicted value must appear verbatim in the passage.

Models that generate text can invent values. Anything not found in the passage is
demoted to "unresolved", which keeps the schema honest.
"""

from __future__ import annotations

from filing_extractor.schema import FIELDS, UNRESOLVED, Extraction
from filing_extractor.textnorm import normalize


def is_grounded(field: str, value: str, passage: str) -> bool:
    if value == UNRESOLVED:
        return True
    haystack = normalize(passage)
    parts = [p.strip() for p in value.split(" | ")] if field == "financial_covenants" else [value]
    return all(normalize(p) in haystack for p in parts)


def ground(extraction: Extraction, passage: str) -> Extraction:
    values = extraction.as_dict()
    for field in FIELDS:
        if not is_grounded(field, values[field], passage):
            values[field] = UNRESOLVED
    return Extraction(**values)
