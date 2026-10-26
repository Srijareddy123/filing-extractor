"""Command line: one passage or a JSONL batch."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from filing_extractor.llm import CacheMiss
from filing_extractor.registry import MODEL_NAMES, Extractor, ModelUnavailable, get_extractor


def run_batch(extractor: Extractor, source: Path, dest: Path, text_key: str = "text") -> int:
    """Read JSONL rows with a text field, write the same rows plus the extracted fields."""
    count = 0
    with source.open(encoding="utf-8") as src, dest.open("w", encoding="utf-8") as out:
        for line_no, line in enumerate(src, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if text_key not in row:
                raise ValueError(f"line {line_no}: missing {text_key!r}")
            row["extraction"] = extractor.extract(row[text_key]).as_dict()
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="filing-extract", description=__doc__)
    parser.add_argument("--model", choices=MODEL_NAMES, default="rules")
    parser.add_argument("--adapter", type=Path, default=None, help="LoRA adapter folder")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("extract", help="extract from one passage")
    group = one.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--file", type=Path)
    batch = sub.add_parser("batch", help="extract from every row of a JSONL file")
    batch.add_argument("input", type=Path)
    batch.add_argument("output", type=Path)
    batch.add_argument("--text-key", default="text")
    args = parser.parse_args(argv)
    try:
        extractor = get_extractor(args.model, args.adapter)
        if args.command == "extract":
            text = args.text if args.text is not None else args.file.read_text(encoding="utf-8")
            print(json.dumps(extractor.extract(text).as_dict(), indent=2))
        else:
            n = run_batch(extractor, args.input, args.output, args.text_key)
            print(f"wrote {n} rows to {args.output}")
    except (ModelUnavailable, CacheMiss, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
