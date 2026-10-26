"""Render the README results block from results/metrics.json, so numbers cannot drift.

`python -m filing_extractor.readme_results` rewrites the block between the two markers in
README.md. The test suite checks that the committed README matches this output.
"""

from __future__ import annotations

import json
from pathlib import Path

from filing_extractor.config import ROOT
from filing_extractor.schema import FIELDS

START, END = "<!-- results:start -->", "<!-- results:end -->"
MODELS = ("rules", "llm", "lora")
LABELS = {
    "rules": "Rules (regex)",
    "llm": "Prompted LLM, structured output",
    "lora": "LoRA fine-tuned small model",
}
HEAD = (
    "| Field | Answerable | Exact match | Answer F1 | EM, answerable only | Unresolved rate "
    "| Answerable but unresolved | Answered but unanswerable |"
)


def _row(name: str, s: dict) -> str:
    return (
        f"| {name} | {s['n_answerable']} | {s['exact_match']:.3f} | {s['answer_f1']:.3f} | "
        f"{s['exact_match_answerable']:.3f} | {s['unresolved_rate']:.3f} | "
        f"{s['answerable_unresolved_rate']:.3f} | {s['false_answer_rate']:.3f} |"
    )


def render_block(metrics: dict, split: str = "test") -> str:
    data = metrics["splits"].get(split, {})
    lines = []
    for model in MODELS:
        if model in data:
            entry = data[model]
            lo, hi = entry["overall_exact_match_ci95"]
            lines += [
                f"**{LABELS[model]}** ({entry['n_passages']} passages, "
                f"{entry['n_documents']} documents, {split} split)",
                "",
                HEAD,
                "|" + "|".join("---" for _ in range(8)) + "|",
            ]
            for field in (*FIELDS, "overall"):
                label = f"**{field}**" if field == "overall" else field
                lines.append(_row(label, entry["fields"][field]))
            lines += [
                "",
                f"Overall exact match 95% interval over documents: {lo:.3f} to {hi:.3f}.",
                "",
            ]
        else:
            status = metrics["status"].get(model, "pending")
            lines += [f"**{LABELS[model]}**: {_status_text(model, status)}", ""]
    return "\n".join(lines).rstrip() + "\n"


def _status_text(model: str, status: str) -> str:
    if model == "llm":
        return (
            "pending. No `ANTHROPIC_API_KEY` was available, so no numbers are reported. "
            "Run `make eval` with a key to fill this in."
        )
    if model == "lora":
        return (
            "pending. Training needs a GPU and has not been run yet; the CPU smoke test "
            "only checks that the code runs. Numbers appear here after the GPU run."
        )
    return status


def update_readme(readme: Path, metrics: dict) -> bool:
    text = readme.read_text(encoding="utf-8")
    head, _, rest = text.partition(START)
    _, _, tail = rest.partition(END)
    new = f"{head}{START}\n{render_block(metrics)}{END}{tail}"
    if new != text:
        readme.write_text(new, encoding="utf-8")
        return True
    return False


def main() -> None:
    metrics = json.loads((ROOT / "results" / "metrics.json").read_text(encoding="utf-8"))
    changed = update_readme(ROOT / "README.md", metrics)
    print("README results block", "updated" if changed else "already current")


if __name__ == "__main__":
    main()
