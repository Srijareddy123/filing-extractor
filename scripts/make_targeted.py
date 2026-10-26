"""Second candidate pass: passages likely to contain a margin, a facility size or a maturity.

Used to balance the label set, because pricing and size statements are rarer than boilerplate.
Like make_candidates.py it picks text only; labels are written by hand afterwards.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
import re
from pathlib import Path

from make_candidates import TRIGGERS, clip, is_junk, paragraphs

MONEY = r"\$\s?\d[\d,\.]*\s?(million|billion)?"
DATE = (
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r" \d{1,2}, ?\d{4}"
)
PATTERNS = {
    "margin": re.compile(
        r"(bear|accrue)s? interest[^.]{0,160}\d+(\.\d+)?%|"
        r"(plus|margin of|spread of)[^.]{0,40}\d+(\.\d+)?%|"
        r"interest rate[^.]{0,80}(equal to|of)[^.]{0,80}\d+(\.\d+)?%",
        re.I,
    ),
    "size": re.compile(
        r"(loan|facility|commitments?|line of credit|note)[^.]{0,80}(amount|sum) of[^.]{0,30}"
        + MONEY
        + r"|up to (an aggregate|a maximum)[^.]{0,40}"
        + MONEY
        + "|"
        + MONEY
        + r"[^.]{0,30}(revolving|term loan|credit facility|line of credit)",
        re.I,
    ),
    "maturity": re.compile(
        r"(maturity date|mature[sd]?|due and payable in full|termination date)[^.]{0,120}" + DATE,
        re.I,
    ),
}
PATTERNS["covenant"] = TRIGGERS["covenant"]
PER_DOC_KIND = {"margin": 2, "size": 2, "maturity": 1, "covenant": 1}


def digest(text: str) -> str:
    return hashlib.md5(re.sub(r"\W+", "", text.lower())[:200].encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dirs", nargs="+", required=True)
    parser.add_argument("--seen", nargs="+", required=True, help="candidate files already used")
    parser.add_argument("--out", required=True)
    parser.add_argument("--start-id", type=int, required=True)
    parser.add_argument("--bonus", type=int, default=0, help="extra passages per kind per doc")
    args = parser.parse_args()
    rng = random.Random(23)
    seen = {
        digest(json.loads(line)["text"])
        for name in args.seen
        for line in Path(name).read_text(encoding="utf-8").splitlines()
    }
    out = []
    for folder in args.dirs:
        for path in sorted(Path(folder).glob("*.txt")):
            text = path.read_text(encoding="utf-8")
            if len(text) < 3000:
                continue
            paras = [p for p in paragraphs(text) if not is_junk(p)]
            for kind, pat in PATTERNS.items():
                budget = PER_DOC_KIND[kind] + args.bonus
                choices = [p for p in paras if pat.search(p)]
                rng.shuffle(choices)
                for p in choices:
                    if budget == 0:
                        break
                    p = clip(p)
                    if digest(p) in seen:
                        continue
                    seen.add(digest(p))
                    out.append({"doc_id": path.stem, "kind": kind, "text": p})
                    budget -= 1
    rng.shuffle(out)
    for i, row in enumerate(out):
        row["id"] = f"p{i + args.start_id:04d}"
    Path(args.out).write_text("\n".join(json.dumps(r) for r in out) + "\n", encoding="utf-8")
    print(len(out), collections.Counter(r["kind"] for r in out))


if __name__ == "__main__":
    main()
