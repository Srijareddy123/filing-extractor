"""Download candidate exhibits to a git-ignored folder as plain text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from filing_extractor.sec import SecClient, html_to_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidates", nargs="?", default="raw/candidates.json")
    parser.add_argument("--out", default="raw/text")
    args = parser.parse_args()
    client = SecClient()
    cands = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for c in cands:
        dest = out / f"{c['adsh']}__{Path(c['file_name']).stem}.txt"
        if dest.exists():
            continue
        try:
            html = client.get(c["url"]).text
        except Exception as exc:  # noqa: BLE001 - report and continue
            print("skip", c["url"], exc)
            continue
        dest.write_text(html_to_text(html), encoding="utf-8")
    print(len(list(out.glob("*.txt"))), "files")


if __name__ == "__main__":
    main()
