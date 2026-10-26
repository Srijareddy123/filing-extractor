"""Prompt text shared by the LLM baseline and the LoRA fine-tune."""

from __future__ import annotations

import json

from filing_extractor.schema import FIELD_HELP, FIELDS, Extraction

PROMPT_VERSION = "v1"

SYSTEM_PROMPT = f"""You read one passage from a public SEC 8-K exhibit (a credit agreement, an amendment or a loan agreement) and fill five fields.

Rules:
- Copy each value exactly as written in the passage. Do not reformat, round or convert.
- If the passage does not state a field for the facility it describes, answer "unresolved". Never guess.
- facility_size: the total size of the facility or loan. Not a sublimit, a fee, a basket, a minimum borrowing amount or an increase cap. If only separate draws are given and no total, answer "unresolved". With several facilities, give the first one stated.
- maturity: the maturity or final termination date. A relative phrase such as "the fifth anniversary of the Closing Date" counts. A date that only limits an extension does not.
- interest_margin: the spread added to a benchmark rate, or the fixed rate when there is no benchmark. Not a default rate, a fee or a benchmark adjustment. A pricing grid with several levels is "unresolved".
- lender: the lender or the administrative agent, by name. "the Lenders" alone is "unresolved".
- financial_covenants: the first maintenance covenant, written as "<ratio or measure name> | <threshold>", both parts copied from the passage. Conditions for baskets, investments or extensions are not covenants.

Fields: {", ".join(FIELDS)}."""

TASK_TEMPLATE = "### Passage\n{passage}\n\n### Answer (JSON)\n"


def build_user_prompt(passage: str) -> str:
    return TASK_TEMPLATE.format(passage=passage.strip())


def target_json(extraction: Extraction) -> str:
    """The exact JSON string the fine-tuned model is trained to produce."""
    return json.dumps(extraction.as_dict(), ensure_ascii=False)


def field_descriptions() -> str:
    return "\n".join(f"- {k}: {v}" for k, v in FIELD_HELP.items())
