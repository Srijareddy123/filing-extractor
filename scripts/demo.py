"""Offline demo: no API key, no GPU, no network. Uses the committed passages and samples."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from fastapi.testclient import TestClient  # noqa: E402

from filing_extractor.api import app  # noqa: E402
from filing_extractor.cli import run_batch  # noqa: E402
from filing_extractor.evaluate import markdown_table, run  # noqa: E402
from filing_extractor.registry import get_extractor  # noqa: E402
from filing_extractor.schema import UNRESOLVED  # noqa: E402
from filing_extractor.stats import build_table  # noqa: E402

OUT = Path("outputs/demo")
SAMPLE = Path("data/sample/demo_input.jsonl")


def show(title: str) -> None:
    print(f"\n=== {title}")


def short(extraction: dict[str, str]) -> str:
    kept = {k: v for k, v in extraction.items() if v != UNRESOLVED}
    return json.dumps(kept) if kept else "(all fields unresolved)"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    show("1. Labeled data (committed in data/passages.jsonl)")
    print(build_table())

    show("2. Rules baseline on the test split (documents the model never saw)")
    result = run(["rules"], ["test"], OUT, None, use_mlflow=True)
    from filing_extractor.metrics import FieldScores
    from filing_extractor.schema import FIELDS

    fields = result["splits"]["test"]["rules"]["fields"]
    print(markdown_table({k: FieldScores(**fields[k]) for k in (*FIELDS, "overall")}))

    show("3. Batch CLI on 8 sample passages (rules)")
    n = run_batch(get_extractor("rules"), SAMPLE, OUT / "rules_sample.jsonl")
    for line in (OUT / "rules_sample.jsonl").read_text(encoding="utf-8").splitlines()[:4]:
        row = json.loads(line)
        print(row["id"], short(row["extraction"]))
    print(f"... {n} rows written to {OUT / 'rules_sample.jsonl'}")

    show("4. Prompted-LLM path with the fake client (canned answers, plumbing only)")
    fake = get_extractor("fake-llm")
    for line in SAMPLE.read_text(encoding="utf-8").splitlines()[:3]:
        row = json.loads(line)
        print(row["id"], short(fake.extract(row["text"]).as_dict()))
    print("These answers are canned, not model output. No metric is computed from them.")

    show("5. FastAPI /extract")
    client = TestClient(app)
    text = json.loads(SAMPLE.read_text(encoding="utf-8").splitlines()[0])["text"]
    response = client.post("/extract", json={"text": text, "model": "rules"})
    print(response.status_code, json.dumps(response.json())[:400])

    show("6. Not run here")
    print("llm  : pending, set ANTHROPIC_API_KEY and run `make eval` (needs the Anthropic API).")
    print("lora : pending, train on a GPU with notebooks/train_lora_colab.ipynb (see README).")


class _Tee:
    """Write to the terminal and to a file, so the output can be rendered for the README."""

    def __init__(self, *streams) -> None:
        self._streams = streams

    def write(self, data: str) -> int:
        for stream in self._streams:
            stream.write(data)
        return len(data)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()


if __name__ == "__main__":
    import contextlib
    import sys

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "demo_output.txt").open("w", encoding="utf-8") as log:
        with contextlib.redirect_stdout(_Tee(sys.stdout, log)):
            main()
