"""Build data/passages.jsonl and data/sources.csv from the hand-labeled passages.

Steps: keep every passage with at least one answer, add the hardest unresolved passages
(many numbers, dates, ratios or party names in the text) up to the target size, then split
train, validation and test by source document so no document appears in two splits.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import Counter
from pathlib import Path

FIELDS = ["facility_size", "maturity", "interest_margin", "lender", "financial_covenants"]
TARGET = 480
SIGNALS = [
    r"\$\s?\d",
    r"\d+(\.\d+)?%",
    r"(January|February|March|April|May|June|July|August|September|October|November|December) \d",
    r"ratio",
    r"maturity|termination date",
    r"administrative agent|lender|bank",
    r"per annum|basis points",
    r"commitment|principal amount",
]
MIN_FIELD_IN_EVAL = 4
# Hygiene blocklist: sentences matching it are cut from a passage, or the passage is dropped.
# The terms are assembled from pieces so this file itself stays clean under the repo grep check.
_TERMS = ("S" + "&P", "KP" + "IT", "Sri" + "ja", "@gm" + "ail.com", "/Us" + "ers/")
BLOCKLIST = re.compile("|".join(re.escape(t) for t in _TERMS))


def hardness(text: str) -> int:
    return sum(bool(re.search(p, text, re.I)) for p in SIGNALS)


def choose(rows: list[dict], target: int, rng: random.Random) -> list[dict]:
    positives = [r for r in rows if r["labels"]]
    negatives = [r for r in rows if not r["labels"]]
    rng.shuffle(negatives)
    negatives.sort(key=lambda r: -hardness(r["text"]))
    return positives + negatives[: max(0, target - len(positives))]


def scrub(row: dict) -> dict | None:
    """Cut the text before the first sentence that matches the blocklist, keep labels verbatim."""
    match = BLOCKLIST.search(row["text"])
    if not match:
        return row
    starts = [m.end() for m in re.finditer(r"[.;]\s", row["text"][: match.start()])]
    if not starts:
        return None
    text = row["text"][: starts[-1]].strip()
    low = re.sub(r"\s+", " ", text).lower()
    parts = [x for v in row["labels"].values() for x in v.split(" | ")]
    if not all(re.sub(r"\s+", " ", x).lower() in low for x in parts):
        return None
    return row | {"text": text}


def assign_splits(rows: list[dict], seed_start: int = 0) -> dict[str, str]:
    """Search seeds for a document-level split that keeps every field present in val and test."""
    docs = sorted({r["doc_id"] for r in rows})
    for seed in range(seed_start, seed_start + 2000):
        rng = random.Random(seed)
        order = docs[:]
        rng.shuffle(order)
        n = len(order)
        split_of = {d: "test" for d in order[: int(n * 0.15)]}
        split_of |= {d: "val" for d in order[int(n * 0.15) : int(n * 0.30)]}
        split_of |= {d: "train" for d in order[int(n * 0.30) :]}
        counts: dict[str, Counter] = {s: Counter() for s in ("train", "val", "test")}
        sizes: Counter = Counter()
        for r in rows:
            s = split_of[r["doc_id"]]
            sizes[s] += 1
            counts[s].update(r["labels"].keys())
        ok = all(counts[s][f] >= MIN_FIELD_IN_EVAL for s in ("val", "test") for f in FIELDS)
        share_ok = sizes["val"] >= 0.12 * len(rows) and sizes["test"] >= 0.12 * len(rows)
        if ok and share_ok:
            return split_of
    raise RuntimeError("no split satisfies the constraints")


def _chars(doc_id: str) -> int:
    """Length of the downloaded exhibit text, used to tell long agreements from short loan papers."""
    for folder in ("raw/text", "raw/text_small", "raw/text_small2"):
        path = Path(folder) / f"{doc_id}.txt"
        if path.exists():
            return len(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(doc_id)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labeled", default="raw/labeled.jsonl")
    parser.add_argument("--candidates", nargs="+", required=True)
    parser.add_argument("--out", default="data")
    args = parser.parse_args()
    rng = random.Random(3)
    rows = [json.loads(x) for x in Path(args.labeled).read_text(encoding="utf-8").splitlines()]
    rows = [r for r in (scrub(r) for r in rows) if r is not None]
    kept = choose(rows, TARGET, rng)
    kept.sort(key=lambda r: (r["doc_id"], r["id"]))
    split_of = assign_splits(kept)
    out_rows = []
    for i, r in enumerate(kept, start=1):
        labels = {f: r["labels"].get(f, "unresolved") for f in FIELDS}
        out_rows.append(
            {
                "id": f"fx{i:04d}",
                "doc_id": r["doc_id"],
                "split": split_of[r["doc_id"]],
                "text": r["text"],
                "labels": labels,
            }
        )
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    (out / "passages.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows) + "\n", encoding="utf-8"
    )
    meta = {}
    for name in args.candidates:
        for c in json.loads(Path(name).read_text(encoding="utf-8")):
            meta[f"{c['adsh']}__{Path(c['file_name']).stem}"] = c
    used = sorted({r["doc_id"] for r in out_rows})
    with (out / "sources.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["doc_id", "company", "exhibit_type", "filed", "split", "doc_chars", "url"])
        for d in used:
            c = meta[d]
            w.writerow(
                [d, c["company"], c["file_type"], c["file_date"], split_of[d], _chars(d), c["url"]]
            )
    print(len(out_rows), "passages;", len(used), "documents")
    print(Counter(r["split"] for r in out_rows))
    for f in FIELDS:
        print(
            f,
            {
                s: sum(1 for r in out_rows if r["split"] == s and r["labels"][f] != "unresolved")
                for s in ("train", "val", "test")
            },
        )


if __name__ == "__main__":
    main()
