"""Prompt and label formatting for the LoRA fine-tune. Pure Python, no torch needed."""

from __future__ import annotations

from dataclasses import dataclass

from filing_extractor.prompt import build_user_prompt, target_json
from filing_extractor.schema import Extraction

INSTRUCTION = (
    "Extract facility_size, maturity, interest_margin, lender and financial_covenants "
    'from the passage. Copy values exactly. Use "unresolved" when the passage does not '
    "state a field.\n\n"
)


def build_prompt(passage: str) -> str:
    return INSTRUCTION + build_user_prompt(passage)


def build_completion(extraction: Extraction, eos: str = "") -> str:
    return target_json(extraction) + eos


@dataclass(frozen=True)
class EncodedExample:
    input_ids: list[int]
    labels: list[int]


def encode_example(
    prompt_ids: list[int], completion_ids: list[int], max_length: int
) -> EncodedExample:
    """Concatenate prompt and answer. The loss covers the answer only (prompt labels = -100).

    When the pair is too long the prompt is cut from the left of its passage side, never
    the answer, so the model always sees a full target.
    """
    room = max_length - len(completion_ids)
    if room <= 0:
        raise ValueError("completion alone is longer than max_length")
    prompt_ids = prompt_ids[-room:] if len(prompt_ids) > room else prompt_ids
    input_ids = prompt_ids + completion_ids
    labels = [-100] * len(prompt_ids) + completion_ids
    return EncodedExample(input_ids=input_ids, labels=labels)


def pad_batch(
    examples: list[EncodedExample], pad_id: int
) -> tuple[list[list[int]], list[list[int]], list[list[int]]]:
    """Right-pad to the longest example. Returns input_ids, attention_mask, labels."""
    longest = max(len(e.input_ids) for e in examples)
    ids, mask, labels = [], [], []
    for e in examples:
        pad = longest - len(e.input_ids)
        ids.append(e.input_ids + [pad_id] * pad)
        mask.append([1] * len(e.input_ids) + [0] * pad)
        labels.append(e.labels + [-100] * pad)
    return ids, mask, labels
