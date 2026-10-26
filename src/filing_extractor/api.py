"""FastAPI service: POST /extract turns a passage into the five-field schema."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from filing_extractor import __version__
from filing_extractor.llm import CacheMiss
from filing_extractor.registry import MODEL_NAMES, Extractor, ModelUnavailable, get_extractor
from filing_extractor.schema import UNRESOLVED, Extraction

MAX_CHARS = 20_000


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS, description="One passage of an exhibit.")
    model: str | None = Field(None, description=f"One of {', '.join(MODEL_NAMES)}.")


class ExtractResponse(BaseModel):
    model: str
    fields: Extraction
    resolved: list[str]


@lru_cache(maxsize=4)
def _extractor(name: str, adapter: str | None) -> Extractor:
    return get_extractor(name, Path(adapter) if adapter else None)


def default_model() -> str:
    return os.environ.get("FX_MODEL", "rules")


app = FastAPI(title="filing-extractor", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "default_model": default_model(), "version": __version__}


@app.post("/extract", response_model=ExtractResponse)
def extract(request: ExtractRequest) -> ExtractResponse:
    name = request.model or default_model()
    if name not in MODEL_NAMES:
        raise HTTPException(status_code=422, detail=f"unknown model {name!r}")
    try:
        extractor = _extractor(name, os.environ.get("FX_LORA_ADAPTER"))
        fields = extractor.extract(request.text)
    except (ModelUnavailable, CacheMiss, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    resolved = [k for k, v in fields.as_dict().items() if v != UNRESOLVED]
    return ExtractResponse(model=name, fields=fields, resolved=resolved)
