"""Search EDGAR full-text for loan and credit agreement exhibits (8-K, EX-10).

Writes raw/candidates.json (large credit agreements) or raw/candidates_small.json
(--small: loan agreements, notes and small facilities).
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from filing_extractor.sec import ExhibitHit, SecClient

QUERIES = [
    '"credit agreement" "administrative agent" "maturity date"',
    '"term loan" "applicable margin" "maturity date"',
    '"amendment" "credit agreement" "revolving commitments"',
    '"loan agreement" "interest rate" "maturity"',
    '"leverage ratio" "credit agreement" "lenders"',
]
QUERIES_SMALL = [
    '"loan and security agreement" "interest rate" "maturity date"',
    '"promissory note" "per annum" "maturity date" loan',
    '"term loan" "prime rate" "maturity date" borrower lender',
    '"revolving line of credit" "interest" "maturity"',
    '"secured promissory note" "interest at" "per annum" borrower',
    '"loan agreement" "bears interest" "fixed rate" maturity',
    '"term loan" "SOFR plus" "margin" maturity borrower lender',
]
WINDOWS = [
    ("2022-01-01", "2022-06-30"),
    ("2022-07-01", "2022-12-31"),
    ("2023-01-01", "2023-06-30"),
    ("2023-07-01", "2023-12-31"),
    ("2024-01-01", "2024-06-30"),
    ("2024-07-01", "2024-12-31"),
    ("2025-01-01", "2025-06-30"),
    ("2025-07-01", "2025-09-30"),
]
KEYWORDS = ("credit", "loan", "financing", "note")
PER_COMPANY = 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--small", action="store_true")
    parser.add_argument("--target", type=int, default=130)
    parser.add_argument("--exclude", default="", help="candidates json whose filings to skip")
    args = parser.parse_args()
    client = SecClient()
    skip: set[str] = set()
    if args.exclude:
        skip = {c["adsh"] for c in json.loads(Path(args.exclude).read_text(encoding="utf-8"))}
    seen: dict[str, ExhibitHit] = {}
    for query in QUERIES_SMALL if args.small else QUERIES:
        for start, end in WINDOWS:
            for hit in client.search_exhibits(query, start, end):
                text = f"{hit.description} {hit.file_name}".lower()
                if hit.adsh not in skip and any(k in text for k in KEYWORDS):
                    seen.setdefault(hit.adsh + hit.file_name, hit)
    pool = list(seen.values())
    random.Random(7).shuffle(pool)
    per_company: dict[str, int] = defaultdict(int)
    chosen: list[ExhibitHit] = []
    for hit in pool:
        if per_company[hit.cik] >= PER_COMPANY:
            continue
        per_company[hit.cik] += 1
        chosen.append(hit)
        if len(chosen) >= args.target:
            break
    out = [h.__dict__ | {"url": h.url} for h in chosen]
    name = "candidates_small2.json" if args.small else "candidates.json"
    Path("raw").mkdir(exist_ok=True)
    Path("raw", name).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"pool={len(pool)} chosen={len(chosen)} companies={len(per_company)}")


if __name__ == "__main__":
    main()
