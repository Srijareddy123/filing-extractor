"""Prompted-LLM baseline with structured output.

The extractor talks to a small client interface so the same code runs with the Anthropic
API, a cache of earlier responses, or a fake client (tests and demo, no network, no key).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from filing_extractor.config import load_env
from filing_extractor.grounding import ground
from filing_extractor.prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from filing_extractor.schema import FIELDS, Extraction

DEFAULT_MODEL = "claude-haiku-4-5"
TOOL_NAME = "record_extraction"


class CacheMiss(RuntimeError):
    """Raised when a cached client has no stored response and no live client behind it."""


class LLMClient(Protocol):
    model_id: str

    def complete(self, system: str, user: str) -> str:
        """Return the model answer as a JSON string."""
        ...


class AnthropicClient:
    """Calls the Anthropic Messages API and forces a tool call so the answer is structured."""

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        import anthropic

        load_env()
        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self.model_id = model or os.environ.get("FX_LLM_MODEL", DEFAULT_MODEL)
        self._client = anthropic.Anthropic(api_key=key)

    def complete(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self.model_id,
            max_tokens=500,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[
                {
                    "name": TOOL_NAME,
                    "description": "Record the five extracted fields.",
                    "input_schema": Extraction.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": TOOL_NAME},
        )
        for block in response.content:
            if block.type == "tool_use":
                return json.dumps(block.input)
        return "{}"


class FakeClient:
    """Deterministic stand-in: answers from a dict keyed by passage, else all unresolved."""

    model_id = "fake"

    def __init__(self, answers: dict[str, Extraction] | None = None) -> None:
        self._answers = answers or {}

    def complete(self, system: str, user: str) -> str:
        for passage, answer in self._answers.items():
            if passage.strip() in user:
                return json.dumps(answer.as_dict())
        return json.dumps(Extraction.empty().as_dict())


class CachedClient:
    """Stores every response in a JSONL file, so reruns and tests need no API."""

    def __init__(self, inner: LLMClient | None, path: Path, model_id: str | None = None) -> None:
        self._inner = inner
        self._path = path
        self.model_id = model_id or (inner.model_id if inner else "cached")
        self._store: dict[str, str] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._store[row["key"]] = row["response"]

    def key(self, system: str, user: str) -> str:
        blob = f"{self.model_id}\n{PROMPT_VERSION}\n{system}\n{user}"
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def has(self, system: str, user: str) -> bool:
        return self.key(system, user) in self._store

    def complete(self, system: str, user: str) -> str:
        key = self.key(system, user)
        if key in self._store:
            return self._store[key]
        if self._inner is None:
            raise CacheMiss("no cached response and no live client")
        response = self._inner.complete(system, user)
        self._store[key] = response
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"key": key, "response": response}) + "\n")
        return response


def parse_response(raw: str) -> Extraction | None:
    """Parse a JSON answer; None when it is not valid for the schema."""
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        return Extraction(**{k: v for k, v in data.items() if k in FIELDS})
    except (json.JSONDecodeError, ValidationError, TypeError):
        return None


class LLMExtractor:
    """Prompted baseline: one call per passage, grounded against the passage text."""

    def __init__(self, client: LLMClient, name: str = "llm") -> None:
        self.client = client
        self.name = name
        self.parse_errors = 0

    def extract(self, text: str) -> Extraction:
        raw = self.client.complete(SYSTEM_PROMPT, build_user_prompt(text))
        parsed = parse_response(raw)
        if parsed is None:
            self.parse_errors += 1
            return Extraction.empty()
        return ground(parsed, text)


def api_key_available() -> bool:
    load_env()
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


__all__ = [
    "AnthropicClient",
    "CacheMiss",
    "CachedClient",
    "FakeClient",
    "LLMClient",
    "LLMExtractor",
    "api_key_available",
    "parse_response",
]
