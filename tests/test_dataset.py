"""Integrity checks on the committed labeled data."""

import csv
from collections import defaultdict
from pathlib import Path

from filing_extractor.data import load_passages
from filing_extractor.grounding import is_grounded
from filing_extractor.schema import FIELDS, UNRESOLVED

PASSAGES = load_passages()


def test_size_is_in_the_required_range() -> None:
    assert 300 <= len(PASSAGES) <= 500


def test_ids_are_unique() -> None:
    assert len({p.id for p in PASSAGES}) == len(PASSAGES)


def test_no_document_crosses_splits() -> None:
    splits_of: dict[str, set[str]] = defaultdict(set)
    for p in PASSAGES:
        splits_of[p.doc_id].add(p.split)
    assert all(len(s) == 1 for s in splits_of.values())


def test_every_label_is_a_verbatim_span() -> None:
    bad = [
        (p.id, f)
        for p in PASSAGES
        for f in FIELDS
        if not is_grounded(f, getattr(p.gold, f), p.text)
    ]
    assert bad == []


def test_every_field_has_answers_in_every_split() -> None:
    for split in ("train", "val", "test"):
        rows = [p for p in PASSAGES if p.split == split]
        for f in FIELDS:
            assert sum(getattr(p.gold, f) != UNRESOLVED for p in rows) >= 4, (split, f)


def test_sources_cover_every_document_and_are_public_sec_urls() -> None:
    with Path("data/sources.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert {r["doc_id"] for r in rows} == {p.doc_id for p in PASSAGES}
    assert all(r["url"].startswith("https://www.sec.gov/Archives/edgar/data/") for r in rows)


def test_covenant_labels_use_the_pipe_format() -> None:
    for p in PASSAGES:
        value = p.gold.financial_covenants
        assert value == UNRESOLVED or value.count(" | ") == 1, p.id
