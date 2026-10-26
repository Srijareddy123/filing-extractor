"""Text normalisation shared by the metrics, the grounding check and the baselines."""

from __future__ import annotations

import re

_SPACE = re.compile(r"\s+")
_EDGE = re.compile(r"^[\s.,;:]+|[\s.,;:]+$")


def normalize(value: str) -> str:
    """Lower-case, collapse whitespace and trim edge punctuation."""
    return _EDGE.sub("", _SPACE.sub(" ", value.lower()))


def tokens(value: str) -> list[str]:
    return normalize(value).split()
