"""The README results block must equal the output of the code, so numbers cannot drift."""

import json
from pathlib import Path

from filing_extractor.readme_results import END, START, render_block

ROOT = Path(__file__).resolve().parents[1]


def test_readme_block_matches_metrics_json() -> None:
    metrics = json.loads((ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    block = readme.split(START, 1)[1].split(END, 1)[0].strip("\n")
    assert block == render_block(metrics, full=False).strip("\n")


def test_docs_results_has_full_table() -> None:
    metrics = json.loads((ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
    doc = (ROOT / "docs" / "RESULTS.md").read_text(encoding="utf-8")
    block = doc.split(START, 1)[1].split(END, 1)[0].strip("\n")
    assert block == render_block(metrics, full=True).strip("\n")


def test_readme_has_no_banned_style() -> None:
    for name in ("README.md", "docs/RESULTS.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        banned = ("\u2014", "\u2013", "seam" + "less", "ro" + "bust", "cutting" + "-edge", "lever" + "age", "del" + "ve")
        for bad in banned:
            assert bad not in text.lower()
