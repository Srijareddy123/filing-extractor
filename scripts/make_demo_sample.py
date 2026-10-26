"""Write the committed demo sample: a few test passages and canned responses for the fake client.

The canned responses are the gold labels of those passages, wrapped as if a model had answered.
They exist only to exercise the LLM code path offline. No metric is computed from them.
"""

from __future__ import annotations

import json
from pathlib import Path

from filing_extractor.data import load_passages
from filing_extractor.llm import CachedClient, FakeClient
from filing_extractor.prompt import SYSTEM_PROMPT, build_user_prompt
from filing_extractor.schema import FIELDS, UNRESOLVED

N_ANSWERED, N_EMPTY = 6, 2


def main() -> None:
    passages = load_passages(split="test")
    answered = [p for p in passages if any(getattr(p.gold, f) != UNRESOLVED for f in FIELDS)]
    empty = [p for p in passages if all(getattr(p.gold, f) == UNRESOLVED for f in FIELDS)]
    chosen = answered[:N_ANSWERED] + empty[:N_EMPTY]
    out = Path("data/sample")
    out.mkdir(parents=True, exist_ok=True)
    (out / "demo_input.jsonl").write_text(
        "\n".join(json.dumps({"id": p.id, "text": p.text}) for p in chosen) + "\n",
        encoding="utf-8",
    )
    cache_path = out / "demo_fake_llm_cache.jsonl"
    cache_path.unlink(missing_ok=True)
    client = CachedClient(FakeClient({p.text: p.gold for p in chosen}), cache_path, model_id="fake")
    for p in chosen:
        client.complete(SYSTEM_PROMPT, build_user_prompt(p.text))
    print(f"wrote {len(chosen)} passages to {out}")


if __name__ == "__main__":
    main()
