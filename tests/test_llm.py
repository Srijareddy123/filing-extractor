import json
from pathlib import Path

import pytest

from filing_extractor.llm import CachedClient, CacheMiss, FakeClient, LLMExtractor, parse_response
from filing_extractor.prompt import SYSTEM_PROMPT, build_user_prompt
from filing_extractor.schema import UNRESOLVED, Extraction

PASSAGE = (
    "Credit Agreement with JPMORGAN CHASE BANK, N.A., as Administrative Agent, for $100,000,000."
)


class CountingClient:
    model_id = "counting"

    def __init__(self, response: str) -> None:
        self.response, self.calls = response, 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        return self.response


def test_parse_response_valid_and_invalid() -> None:
    assert parse_response('{"lender": "A Bank"}').lender == "A Bank"
    assert parse_response("not json") is None
    assert parse_response("[1, 2]") is None


def test_extractor_grounds_output() -> None:
    answer = Extraction(facility_size="$100,000,000", lender="Invented Bank")
    out = LLMExtractor(FakeClient({PASSAGE: answer})).extract(PASSAGE)
    assert out.facility_size == "$100,000,000"
    assert out.lender == UNRESOLVED


def test_bad_json_counts_a_parse_error_and_returns_unresolved() -> None:
    extractor = LLMExtractor(CountingClient("oops"))
    out = extractor.extract(PASSAGE)
    assert extractor.parse_errors == 1
    assert all(v == UNRESOLVED for v in out.as_dict().values())


def test_cache_calls_live_client_once(tmp_path: Path) -> None:
    inner = CountingClient(json.dumps({"lender": "JPMORGAN CHASE BANK, N.A."}))
    cache = tmp_path / "cache.jsonl"
    first = CachedClient(inner, cache)
    first.complete(SYSTEM_PROMPT, build_user_prompt(PASSAGE))
    again = CachedClient(inner, cache)  # new object, reads the file
    again.complete(SYSTEM_PROMPT, build_user_prompt(PASSAGE))
    assert inner.calls == 1
    assert again.has(SYSTEM_PROMPT, build_user_prompt(PASSAGE))


def test_cache_only_client_raises_on_miss(tmp_path: Path) -> None:
    client = CachedClient(None, tmp_path / "empty.jsonl", model_id="x")
    with pytest.raises(CacheMiss):
        client.complete("s", "u")


def test_demo_cache_matches_prompt_version() -> None:
    from filing_extractor.registry import get_extractor

    sample = Path("data/sample/demo_input.jsonl").read_text(encoding="utf-8").splitlines()
    text = json.loads(sample[0])["text"]
    assert isinstance(get_extractor("fake-llm").extract(text), Extraction)
