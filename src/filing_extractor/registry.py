"""Pick an extractor by name: rules, llm, fake-llm or lora."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from filing_extractor.config import DATA_DIR, ROOT
from filing_extractor.llm import (
    AnthropicClient,
    CachedClient,
    LLMExtractor,
    api_key_available,
)
from filing_extractor.rules import RulesExtractor
from filing_extractor.schema import Extraction

MODEL_NAMES = ("rules", "llm", "fake-llm", "lora")
LLM_CACHE = ROOT / "results" / "llm_cache.jsonl"
DEMO_CACHE = DATA_DIR / "sample" / "demo_fake_llm_cache.jsonl"
DEFAULT_ADAPTER = ROOT / "outputs" / "lora-qwen2.5-0.5b"


def _display(path: Path) -> str:
    """Show repo-relative paths so messages and result files carry no machine paths."""
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


class Extractor(Protocol):
    name: str

    def extract(self, text: str) -> Extraction: ...


class ModelUnavailable(RuntimeError):
    """The requested model cannot run here (no key, no adapter, no GPU run yet)."""


def llm_cached_client() -> CachedClient:
    """Live client when a key is set, otherwise a cache-only client."""
    inner = AnthropicClient() if api_key_available() else None
    return CachedClient(inner, LLM_CACHE)


def get_extractor(name: str, adapter: Path | None = None) -> Extractor:
    if name == "rules":
        return RulesExtractor()
    if name == "fake-llm":
        return LLMExtractor(CachedClient(None, DEMO_CACHE, model_id="fake"), name="fake-llm")
    if name == "llm":
        return LLMExtractor(llm_cached_client(), name="llm")
    if name == "lora":
        folder = adapter or Path(os.environ.get("FX_LORA_ADAPTER", DEFAULT_ADAPTER))
        if not (folder / "adapter_config.json").exists():
            raise ModelUnavailable(f"no LoRA adapter at {_display(folder)} (train on a GPU first)")
        from filing_extractor.lora_infer import LoraExtractor

        return LoraExtractor(folder)
    raise ValueError(f"unknown model {name!r}, choose from {MODEL_NAMES}")
