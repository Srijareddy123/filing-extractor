"""Load the labeled passages."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from filing_extractor.config import DATA_DIR
from filing_extractor.schema import Extraction

SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class Passage:
    id: str
    doc_id: str
    split: str
    text: str
    gold: Extraction


def load_passages(path: Path | None = None, split: str | None = None) -> list[Passage]:
    """Read data/passages.jsonl, optionally keeping one split."""
    source = path or DATA_DIR / "passages.jsonl"
    if split is not None and split not in SPLITS:
        raise ValueError(f"split must be one of {SPLITS}, got {split!r}")
    rows = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        if split is None or raw["split"] == split:
            rows.append(
                Passage(
                    id=raw["id"],
                    doc_id=raw["doc_id"],
                    split=raw["split"],
                    text=raw["text"],
                    gold=Extraction(**raw["labels"]),
                )
            )
    return rows


LONG_DOC_CHARS = 80_000


def load_doc_kinds(path: Path | None = None) -> dict[str, str]:
    """Map doc_id to "long" (full credit agreement text) or "short" (amendment, loan paper)."""
    source = path or DATA_DIR / "sources.csv"
    with source.open(encoding="utf-8", newline="") as fh:
        return {
            row["doc_id"]: "long" if int(row["doc_chars"]) >= LONG_DOC_CHARS else "short"
            for row in csv.DictReader(fh)
        }
