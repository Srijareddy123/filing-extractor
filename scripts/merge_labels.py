"""Merge hand-written label batches with the candidate passages and validate them.

Each label value must be a verbatim span of the passage (whitespace-normalised, case-insensitive);
covenant labels are "<ratio name> | <threshold>" where both parts are verbatim spans.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KEYS = {
    "s": "facility_size",
    "m": "maturity",
    "i": "interest_margin",
    "l": "lender",
    "c": "financial_covenants",
}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def check(label_key: str, value: str, passage: str, pid: str) -> list[str]:
    parts = [p.strip() for p in value.split(" | ")] if label_key == "c" else [value]
    return [
        f"{pid} {KEYS[label_key]}: not verbatim: {part!r}"
        for part in parts
        if norm(part) not in norm(passage)
    ]


def main() -> int:
    cands = {}
    for cand_file in sys.argv[1].split(","):
        for line in Path(cand_file).read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            cands[row["id"]] = row
    labels: dict[str, dict] = {}
    dropped: set[str] = set()
    for path in sorted(Path(sys.argv[2]).glob("b*.json")):
        batch = json.loads(path.read_text(encoding="utf-8"))
        dropped.update(batch.pop("_drop", []))
        labels.update(batch)
    errors: list[str] = []
    out = []
    for pid, lab in labels.items():
        if pid in dropped:
            continue
        if pid not in cands:
            errors.append(f"{pid}: unknown id")
            continue
        row = cands[pid]
        for k, v in lab.items():
            errors += check(k, v, row["text"], pid)
        out.append(
            {
                "id": pid,
                "doc_id": row["doc_id"],
                "text": row["text"],
                "labels": {KEYS[k]: v for k, v in lab.items()},
            }
        )
    unlabeled = [p for p in cands if p not in labels and p not in dropped]
    print("labeled", len(out), "unlabeled", len(unlabeled), "errors", len(errors))
    for e in errors:
        print(e)
    Path(sys.argv[3]).write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
