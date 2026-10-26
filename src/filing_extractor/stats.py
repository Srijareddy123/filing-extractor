"""Dataset statistics: passages, documents and answerable counts per split and field."""

from __future__ import annotations

from collections import defaultdict

from filing_extractor.config import ROOT
from filing_extractor.data import SPLITS, load_passages
from filing_extractor.schema import FIELDS, UNRESOLVED


def build_table() -> str:
    passages = load_passages()
    docs: dict[str, set[str]] = defaultdict(set)
    counts: dict[str, int] = defaultdict(int)
    answers: dict[tuple[str, str], int] = defaultdict(int)
    for p in passages:
        docs[p.split].add(p.doc_id)
        counts[p.split] += 1
        for f in FIELDS:
            if getattr(p.gold, f) != UNRESOLVED:
                answers[(p.split, f)] += 1
    head = "| Split | Documents | Passages | " + " | ".join(FIELDS) + " |"
    rule = "|" + "|".join("---" for _ in range(3 + len(FIELDS))) + "|"
    rows = [head, rule]
    for split in (*SPLITS, "all"):
        keys = SPLITS if split == "all" else (split,)
        n_docs = len(set().union(*(docs[k] for k in keys)))
        n = sum(counts[k] for k in keys)
        cells = [str(sum(answers[(k, f)] for k in keys)) for f in FIELDS]
        rows.append(f"| {split} | {n_docs} | {n} | " + " | ".join(cells) + " |")
    note = (
        "\n\nThe field columns count passages where the field has an answer; "
        "every other passage-field pair is `unresolved`.\n"
    )
    return "\n".join(rows) + note


def main() -> None:
    table = build_table()
    out = ROOT / "results" / "dataset_stats.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(table, encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
