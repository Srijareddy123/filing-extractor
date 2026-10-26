"""Pick candidate passages from downloaded exhibits for manual labeling.

Selection uses broad topic triggers (and random boilerplate paragraphs as negatives).
It does not pre-fill any label: every label is written by hand afterwards.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

MONEY = r"\$\s?\d[\d,\.]*\s?(million|billion)?"
DATE = r"(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, ?\d{4}"
TRIGGERS = {
    "size": re.compile(
        r"(aggregate|total|original|initial)[^.]{0,60}(principal )?(amount|commitments?)[^.]{0,40}"
        + MONEY
        + "|credit agreement[^.]{0,80}"
        + MONEY
        + "|^[^a-z]{0,20}"
        + MONEY
        + r" (senior )?(secured |unsecured )?(revolving |term )?(credit|loan)",
        re.I,
    ),
    "maturity": re.compile(
        r"(maturity|termination) date[^.]{0,80}(means|shall be|is|occurs)[^.]{0,120}"
        + "("
        + DATE
        + r"|anniversary)|(mature|matures|due and payable) on[^.]{0,30}"
        + DATE,
        re.I,
    ),
    "margin": re.compile(
        r"\d\.\d+%[^.]{0,40}per annum|per annum[^.]{0,40}\d\.\d+%|plus[^.]{0,30}\d\.\d+%|"
        r"(applicable )?(margin|spread)[^.]{0,40}\d\.\d+%|\d+ basis points",
        re.I,
    ),
    "covenant": re.compile(
        r"(ratio)[^.]{0,200}(\d\.\d+ ?(to|:) ?1(\.0+)?)|(\d\.\d+ ?(to|:) ?1(\.0+)?)[^.]{0,200}ratio",
        re.I,
    ),
}
MAX_LEN = 950
MIN_LEN = 140
PER_DOC = 5


def clip(text: str) -> str:
    if len(text) <= MAX_LEN:
        return text
    cut = text[:MAX_LEN]
    end = max(cut.rfind(". "), cut.rfind("; "))
    return cut[: end + 1] if end > MIN_LEN else cut


def paragraphs(text: str) -> list[str]:
    paras = [p.strip() for p in text.split("\n\n")]
    merged: list[str] = []
    buf = ""
    for p in paras:
        if len(p) < 60 and not buf:
            buf = p
            continue
        cand = f"{buf} {p}".strip() if buf else p
        buf = ""
        merged.append(cand)
    return merged


def is_junk(p: str) -> bool:
    if len(p) < MIN_LEN:
        return True
    if p.count("....") or len(re.findall(r"\bSection \d", p)) > 6:
        return True
    letters = sum(c.isalpha() for c in p)
    return letters / len(p) < 0.6


def main() -> None:
    rng = random.Random(11)
    out = []
    seen: set[str] = set()
    for path in sorted(Path("raw/text").glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        if len(text) < 8000:
            continue
        paras = [p for p in paragraphs(text) if not is_junk(p)]
        if len(paras) < 20:
            continue
        buckets: dict[str, list[str]] = {}
        for name, pat in TRIGGERS.items():
            buckets[name] = [p for p in paras if pat.search(p)]
        buckets["lender"] = [
            p
            for p in paras[:15] + paras[-40:]
            if re.search(r"as (the )?administrative agent|^.{0,80}LENDER:", p, re.I)
            and re.search(r"[A-Z]{4,}", p)
        ]
        kinds = [k for k in buckets if buckets[k]]
        rng.shuffle(kinds)
        if rng.random() < 0.25:
            buckets["random"] = paras
            kinds.append("random")
        picked = 0
        for kind in kinds:
            if picked >= PER_DOC:
                break
            choices = buckets[kind][:]
            rng.shuffle(choices)
            for p in choices:
                p = clip(p)
                key = hashlib.md5(re.sub(r"\W+", "", p.lower())[:200].encode()).hexdigest()
                if key in seen:
                    continue
                seen.add(key)
                out.append({"doc_id": path.stem, "kind": kind, "text": p})
                picked += 1
                break
    for i, row in enumerate(out):
        row["id"] = f"p{i + 1000:04d}"
    Path("raw/cands.jsonl").write_text(
        "\n".join(json.dumps(r) for r in out) + "\n", encoding="utf-8"
    )
    docs = {r["doc_id"] for r in out}
    print(len(out), "passages from", len(docs), "documents")


if __name__ == "__main__":
    main()
