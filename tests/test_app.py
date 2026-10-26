import json
from pathlib import Path

from fastapi.testclient import TestClient

from filing_extractor.api import app
from filing_extractor.cli import main as cli_main
from filing_extractor.cli import run_batch
from filing_extractor.registry import get_extractor

client = TestClient(app)
TEXT = (
    "Credit Agreement among ACME, and CITIBANK, N.A., as Administrative Agent, providing a "
    "revolving credit facility in an aggregate principal amount of $250,000,000."
)


def test_health() -> None:
    assert client.get("/health").json()["status"] == "ok"


def test_extract_rules() -> None:
    r = client.post("/extract", json={"text": TEXT, "model": "rules"})
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "rules"
    assert body["fields"]["facility_size"] == "$250,000,000"
    assert "facility_size" in body["resolved"]


def test_extract_validates_input() -> None:
    assert client.post("/extract", json={"text": ""}).status_code == 422
    assert client.post("/extract", json={"text": TEXT, "model": "nope"}).status_code == 422


def test_lora_without_adapter_is_503(monkeypatch) -> None:
    monkeypatch.setenv("FX_LORA_ADAPTER", "/nonexistent")
    r = client.post("/extract", json={"text": TEXT, "model": "lora"})
    assert r.status_code == 503


def test_llm_without_key_or_cache_is_503() -> None:
    r = client.post("/extract", json={"text": "No cached answer for this one.", "model": "llm"})
    assert r.status_code == 503


def test_batch_roundtrip(tmp_path: Path) -> None:
    src, dest = tmp_path / "in.jsonl", tmp_path / "out.jsonl"
    src.write_text(json.dumps({"id": "a", "text": TEXT}) + "\n\n", encoding="utf-8")
    assert run_batch(get_extractor("rules"), src, dest) == 1
    row = json.loads(dest.read_text(encoding="utf-8"))
    assert row["id"] == "a" and row["extraction"]["facility_size"] == "$250,000,000"


def test_cli_extract_and_errors(capsys, tmp_path: Path) -> None:
    assert cli_main(["extract", "--text", TEXT]) == 0
    assert "$250,000,000" in capsys.readouterr().out
    assert cli_main(["--model", "lora", "--adapter", str(tmp_path), "extract", "--text", TEXT]) == 1
    assert cli_main(["batch", str(tmp_path / "missing.jsonl"), str(tmp_path / "o.jsonl")]) == 1
