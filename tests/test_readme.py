"""The README results block must equal the output of the code, so numbers cannot drift."""

import json
from pathlib import Path

from filing_extractor.readme_results import END, START, render_block

ROOT = Path(__file__).resolve().parents[1]


def test_readme_block_matches_metrics_json() -> None:
    metrics = json.loads((ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    block = readme.split(START, 1)[1].split(END, 1)[0].strip("\n")
    assert block == render_block(metrics).strip("\n")


def test_readme_has_no_banned_style() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for bad in ("—", "–", "seamless", "robust", "cutting-edge", "leverage", "delve"):
        assert bad not in readme.lower()
