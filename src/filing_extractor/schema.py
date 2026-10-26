"""Pydantic schema for the five extracted fields.

A field the text cannot support holds the literal string "unresolved" instead of a guess.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator

UNRESOLVED: Final = "unresolved"
FIELDS: Final = (
    "facility_size",
    "maturity",
    "interest_margin",
    "lender",
    "financial_covenants",
)

FIELD_HELP: Final = {
    "facility_size": "Dollar amount of the facility, as written (for example $500,000,000).",
    "maturity": "Maturity date as written, or a relative phrase such as 'the fifth anniversary'.",
    "interest_margin": "Spread over the benchmark rate, or the fixed rate, as written (1.75%).",
    "lender": "Name of the lender or the administrative agent, as written.",
    "financial_covenants": "'<ratio name> | <threshold>' for the first maintenance covenant.",
}


class Extraction(BaseModel):
    """Structured loan terms from one passage."""

    model_config = ConfigDict(extra="ignore")

    facility_size: str = Field(UNRESOLVED, description=FIELD_HELP["facility_size"])
    maturity: str = Field(UNRESOLVED, description=FIELD_HELP["maturity"])
    interest_margin: str = Field(UNRESOLVED, description=FIELD_HELP["interest_margin"])
    lender: str = Field(UNRESOLVED, description=FIELD_HELP["lender"])
    financial_covenants: str = Field(UNRESOLVED, description=FIELD_HELP["financial_covenants"])

    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_unresolved(cls, value: object) -> object:
        if value is None:
            return UNRESOLVED
        if isinstance(value, str) and (not value.strip() or value.strip().lower() in _EMPTY):
            return UNRESOLVED
        return value.strip() if isinstance(value, str) else str(value)

    def as_dict(self) -> dict[str, str]:
        return self.model_dump()

    @classmethod
    def empty(cls) -> Extraction:
        return cls()


_EMPTY: Final = {"unresolved", "none", "null", "n/a", "not stated", "unknown"}
