"""Error analysis: group wrong predictions into patterns and print examples."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from filing_extractor.data import Passage, load_passages
from filing_extractor.schema import FIELDS, UNRESOLVED, Extraction
from filing_extractor.textnorm import normalize, tokens

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
KIND_TEXT = {
    "missed": "gold has an answer, model said unresolved",
    "false_answer": "gold is unresolved, model gave a value",
    "boundary": "both give a value and the spans overlap but differ",
    "wrong_value": "both give a value and the spans do not overlap",
}


@dataclass(frozen=True)
class ErrorCase:
    passage_id: str
    doc_id: str
    field: str
    kind: str
    gold: str
    pred: str
    text: str


def classify(pred: str, gold: str) -> str | None:
    """Error kind for one (prediction, gold) pair, None when it is correct."""
    if normalize(pred) == normalize(gold):
        return None
    if pred == UNRESOLVED:
        return "missed"
    if gold == UNRESOLVED:
        return "false_answer"
    return "boundary" if set(tokens(pred)) & set(tokens(gold)) else "wrong_value"


def find_errors(passages: list[Passage], preds: list[Extraction]) -> list[ErrorCase]:
    cases = []
    for p, pred in zip(passages, preds, strict=True):
        for field in FIELDS:
            kind = classify(getattr(pred, field), getattr(p.gold, field))
            if kind:
                cases.append(
                    ErrorCase(
                        p.id,
                        p.doc_id,
                        field,
                        kind,
                        getattr(p.gold, field),
                        getattr(pred, field),
                        p.text,
                    )
                )
    return cases


def top_patterns(
    cases: list[ErrorCase], k: int = 3
) -> list[tuple[tuple[str, str], list[ErrorCase]]]:
    groups: dict[tuple[str, str], list[ErrorCase]] = defaultdict(list)
    for c in cases:
        groups[(c.field, c.kind)].append(c)
    ranked = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    return ranked[:k]


def load_predictions(model: str, split: str, results_dir: Path) -> dict[str, Extraction]:
    path = results_dir / "predictions" / f"{model}_{split}.jsonl"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return {r["id"]: Extraction(**r["pred"]) for r in rows}


def render(model: str, splits: list[str], cases: list[ErrorCase], total: int, examples: int) -> str:
    kinds = Counter(c.kind for c in cases)
    lines = [
        f"# Error analysis: {model} on {' + '.join(splits)}",
        "",
        f"{len(cases)} wrong (passage, field) pairs out of {total}. "
        f"By kind: " + ", ".join(f"{k} {v}" for k, v in kinds.most_common()) + ".",
        "",
    ]
    lines += ["| Field | " + " | ".join(KIND_TEXT) + " |", "|---|" + "---|" * len(KIND_TEXT)]
    for field in FIELDS:
        counts = [sum(1 for c in cases if c.field == field and c.kind == k) for k in KIND_TEXT]
        lines.append(f"| {field} | " + " | ".join(str(n) for n in counts) + " |")
    lines.append("")
    for n, ((field, kind), group) in enumerate(top_patterns(cases), start=1):
        lines += [
            f"## Pattern {n}: {field}, {kind} ({len(group)} cases)",
            "",
            KIND_TEXT[kind] + ".",
            "",
        ]
        for c in group[:examples]:
            snippet = c.text if len(c.text) <= 420 else c.text[:420] + " ..."
            lines += [
                f"- `{c.passage_id}` gold: `{c.gold}` | predicted: `{c.pred}`",
                f"  > {snippet}",
                "",
            ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default="rules")
    p.add_argument("--splits", nargs="+", default=["val", "test"])
    p.add_argument("--results", type=Path, default=RESULTS_DIR)
    p.add_argument("--examples", type=int, default=2)
    args = p.parse_args(argv)
    cases: list[ErrorCase] = []
    total = 0
    for split in args.splits:
        passages = load_passages(split=split)
        by_id = load_predictions(args.model, split, args.results)
        preds = [by_id[p.id] for p in passages]
        cases += find_errors(passages, preds)
        total += len(passages) * len(FIELDS)
    report = render(args.model, args.splits, cases, total, args.examples)
    out = args.results / f"error_analysis_{args.model}.md"
    out.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
