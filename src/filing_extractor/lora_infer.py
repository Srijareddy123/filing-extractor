"""Inference with a trained LoRA adapter."""

from __future__ import annotations

import json
import re
from pathlib import Path

from filing_extractor.grounding import ground
from filing_extractor.llm import parse_response
from filing_extractor.lora_format import build_prompt
from filing_extractor.schema import Extraction

_JSON = re.compile(r"\{.*?\}", re.S)


def parse_generation(text: str) -> Extraction | None:
    """Pull the first JSON object out of generated text."""
    match = _JSON.search(text)
    return parse_response(match.group(0)) if match else None


class LoraExtractor:
    """Loads the base model named in the adapter folder and applies the adapter."""

    def __init__(self, adapter_dir: Path, max_new_tokens: int = 200) -> None:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        config = json.loads((adapter_dir / "adapter_config.json").read_text(encoding="utf-8"))
        base = config["base_model_name_or_path"]
        self.name = "lora"
        self.parse_errors = 0
        self._max_new = max_new_tokens
        self._torch = torch
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if self._device == "cuda" else torch.float32
        self._tok = AutoTokenizer.from_pretrained(base)
        model = AutoModelForCausalLM.from_pretrained(base, dtype=dtype)
        self._model = PeftModel.from_pretrained(model, adapter_dir).to(self._device).eval()

    def extract(self, text: str) -> Extraction:
        torch = self._torch
        inputs = self._tok(build_prompt(text), return_tensors="pt", add_special_tokens=False)
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self._model.generate(
                **inputs,
                max_new_tokens=self._max_new,
                do_sample=False,
                pad_token_id=self._tok.pad_token_id or self._tok.eos_token_id,
            )
        generated = self._tok.decode(
            out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )
        parsed = parse_generation(generated)
        if parsed is None:
            self.parse_errors += 1
            return Extraction.empty()
        return ground(parsed, text)
