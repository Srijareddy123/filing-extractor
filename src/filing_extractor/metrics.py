"""Metrics: exact match, token F1, unresolved rate, answerable-but-unresolved rate.

Every (passage, field) pair is one item. A pair counts as correct when the normalised
prediction equals the normalised gold value, and "unresolved" equals "unresolved".
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from filing_extractor.schema import FIELDS, UNRESOLVED, Extraction
from filing_extractor.textnorm import normalize, tokens


def exact_match(pred: str, gold: str) -> float:
    return float(normalize(pred) == normalize(gold))


def token_f1(pred: str, gold: str) -> float:
    """SQuAD-style token F1. Two unresolved values score 1, one unresolved scores 0."""
    pred_unres, gold_unres = pred == UNRESOLVED, gold == UNRESOLVED
    if pred_unres or gold_unres:
        return float(pred_unres and gold_unres)
    p, g = tokens(pred), tokens(gold)
    overlap = sum((Counter(p) & Counter(g)).values())
    if overlap == 0:
        return 0.0
    precision, recall = overlap / len(p), overlap / len(g)
    return 2 * precision * recall / (precision + recall)


@dataclass(frozen=True)
class FieldScores:
    n: int
    n_answerable: int
    exact_match: float
    f1: float
    answer_precision: float
    answer_recall: float
    answer_f1: float
    exact_match_answerable: float
    unresolved_rate: float
    answerable_unresolved_rate: float
    false_answer_rate: float

    def as_dict(self) -> dict[str, float | int]:
        return self.__dict__.copy()


def _safe(num: float, den: int) -> float:
    return num / den if den else 0.0


def score_pairs(pairs: Sequence[tuple[str, str]]) -> FieldScores:
    """Score a list of (prediction, gold) value pairs.

    exact_match and f1 count every pair, so an unresolved prediction on an unresolved gold
    value is a hit. answer_precision, answer_recall and answer_f1 look only at answers:
    a hit is a predicted value that equals a gold value.
    """
    n = len(pairs)
    answerable = [(p, g) for p, g in pairs if g != UNRESOLVED]
    unanswerable = [(p, g) for p, g in pairs if g == UNRESOLVED]
    answered = [(p, g) for p, g in pairs if p != UNRESOLVED]
    hits = sum(exact_match(p, g) for p, g in answered if g != UNRESOLVED)
    precision, recall = _safe(hits, len(answered)), _safe(hits, len(answerable))
    return FieldScores(
        n=n,
        n_answerable=len(answerable),
        exact_match=_safe(sum(exact_match(p, g) for p, g in pairs), n),
        f1=_safe(sum(token_f1(p, g) for p, g in pairs), n),
        answer_precision=precision,
        answer_recall=recall,
        answer_f1=_safe(2 * precision * recall, precision + recall),
        exact_match_answerable=_safe(
            sum(exact_match(p, g) for p, g in answerable), len(answerable)
        ),
        unresolved_rate=_safe(sum(p == UNRESOLVED for p, _ in pairs), n),
        answerable_unresolved_rate=_safe(
            sum(p == UNRESOLVED for p, _ in answerable), len(answerable)
        ),
        false_answer_rate=_safe(sum(p != UNRESOLVED for p, _ in unanswerable), len(unanswerable)),
    )


def evaluate(preds: Sequence[Extraction], golds: Sequence[Extraction]) -> dict[str, FieldScores]:
    """Per-field scores plus an 'overall' entry over all fields."""
    if len(preds) != len(golds):
        raise ValueError("preds and golds must have the same length")
    per_field: dict[str, FieldScores] = {}
    all_pairs: list[tuple[str, str]] = []
    for field in FIELDS:
        pairs = [(getattr(p, field), getattr(g, field)) for p, g in zip(preds, golds, strict=True)]
        per_field[field] = score_pairs(pairs)
        all_pairs.extend(pairs)
    per_field["overall"] = score_pairs(all_pairs)
    return per_field


def bootstrap_ci(
    preds: Sequence[Extraction],
    golds: Sequence[Extraction],
    doc_ids: Sequence[str],
    n_boot: int = 1000,
    seed: int = 0,
) -> tuple[float, float]:
    """95% interval for overall exact match, resampling whole source documents."""
    by_doc: dict[str, list[float]] = {}
    for p, g, d in zip(preds, golds, doc_ids, strict=True):
        by_doc.setdefault(d, []).extend(exact_match(getattr(p, f), getattr(g, f)) for f in FIELDS)
    docs = list(by_doc)
    rng = random.Random(seed)
    stats = []
    for _ in range(n_boot):
        sample = [by_doc[rng.choice(docs)] for _ in docs]
        flat = [x for items in sample for x in items]
        stats.append(sum(flat) / len(flat))
    stats.sort()
    return stats[int(0.025 * n_boot)], stats[int(0.975 * n_boot) - 1]
