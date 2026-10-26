import json
from pathlib import Path

from filing_extractor.data import load_passages
from filing_extractor.errors import classify, find_errors, top_patterns
from filing_extractor.evaluate import markdown_table, run
from filing_extractor.lora_format import encode_example, pad_batch
from filing_extractor.lora_infer import parse_generation
from filing_extractor.rules import RulesExtractor
from filing_extractor.schema import FIELDS, UNRESOLVED


def test_run_writes_tables_predictions_and_pending_status(tmp_path: Path) -> None:
    result = run(["rules", "llm", "lora"], ["val"], tmp_path, tmp_path / "no-adapter", False)
    assert "rules" in result["splits"]["val"]
    assert result["status"]["rules"] == "ok"
    assert result["status"]["llm"].startswith("pending")
    assert result["status"]["lora"].startswith("pending")
    assert (tmp_path / "predictions" / "rules_val.jsonl").exists()
    text = (tmp_path / "results.md").read_text(encoding="utf-8")
    assert "Not run." in text and "| overall |" in text.replace("**", "")


def test_error_kinds() -> None:
    assert classify("a", "a") is None
    assert classify(UNRESOLVED, "a") == "missed"
    assert classify("a", UNRESOLVED) == "false_answer"
    assert classify("big deal", "deal") == "boundary"
    assert classify("x", "y") == "wrong_value"


def test_top_patterns_orders_by_count() -> None:
    passages = load_passages(split="val")
    preds = [RulesExtractor().extract(p.text) for p in passages]
    cases = find_errors(passages, preds)
    patterns = top_patterns(cases, 3)
    sizes = [len(group) for _, group in patterns]
    assert sizes == sorted(sizes, reverse=True)
    assert all(field in FIELDS for (field, _), _ in patterns)


def test_encode_example_masks_prompt_and_keeps_answer() -> None:
    ex = encode_example([1, 2, 3, 4, 5], [9, 8], max_length=5)
    assert ex.input_ids == [3, 4, 5, 9, 8]
    assert ex.labels == [-100, -100, -100, 9, 8]


def test_pad_batch_pads_with_ignored_labels() -> None:
    a = encode_example([1, 2], [7], max_length=10)
    b = encode_example([1], [7], max_length=10)
    ids, mask, labels = pad_batch([a, b], pad_id=0)
    assert ids[1] == [1, 7, 0] and mask[1] == [1, 1, 0] and labels[1] == [-100, 7, -100]


def test_parse_generation_finds_json_in_text() -> None:
    out = parse_generation('noise {"lender": "A Bank", "maturity": "unresolved"} trailing')
    assert out is not None and out.lender == "A Bank"
    assert parse_generation("no json here") is None


def test_markdown_table_has_all_rows() -> None:
    from filing_extractor.metrics import evaluate
    from filing_extractor.schema import Extraction

    table = markdown_table(evaluate([Extraction()], [Extraction()]))
    assert table.count("\n") == len(FIELDS) + 2


def test_json_results_roundtrip(tmp_path: Path) -> None:
    run(["rules"], ["test"], tmp_path, None, False)
    data = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert data["splits"]["test"]["rules"]["fields"]["overall"]["n"] > 0
