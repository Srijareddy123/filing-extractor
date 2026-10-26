import pytest

from filing_extractor.metrics import bootstrap_ci, evaluate, exact_match, score_pairs, token_f1
from filing_extractor.schema import FIELDS, UNRESOLVED, Extraction


def test_blank_and_none_become_unresolved() -> None:
    e = Extraction(facility_size=None, maturity="  ", lender="None", interest_margin="1.5%")
    assert e.facility_size == UNRESOLVED
    assert e.maturity == UNRESOLVED
    assert e.lender == UNRESOLVED
    assert e.interest_margin == "1.5%"


def test_extra_keys_are_ignored() -> None:
    assert Extraction(**{"lender": "A Bank", "note": "x"}).lender == "A Bank"


def test_exact_match_ignores_case_space_and_edge_punctuation() -> None:
    assert exact_match(" $5,000,000. ", "$5,000,000")
    assert exact_match("Wells  Fargo", "wells fargo")
    assert not exact_match("$5,000,000", "$6,000,000")


def test_token_f1_cases() -> None:
    assert token_f1(UNRESOLVED, UNRESOLVED) == 1.0
    assert token_f1(UNRESOLVED, "x") == 0.0
    assert token_f1("x", UNRESOLVED) == 0.0
    assert token_f1("a b c", "a b c") == 1.0
    assert token_f1("a b", "a b c d") == pytest.approx(2 * 1.0 * 0.5 / 1.5)
    assert token_f1("z", "a b") == 0.0


def test_score_pairs_hand_computed() -> None:
    pairs = [
        ("A", "A"),  # hit
        ("B", "C"),  # wrong value
        (UNRESOLVED, "D"),  # answerable but unresolved
        (UNRESOLVED, UNRESOLVED),  # correct refusal
        ("E", UNRESOLVED),  # answered but unanswerable
    ]
    s = score_pairs(pairs)
    assert s.n == 5 and s.n_answerable == 3
    assert s.exact_match == pytest.approx(2 / 5)
    assert s.exact_match_answerable == pytest.approx(1 / 3)
    assert s.unresolved_rate == pytest.approx(2 / 5)
    assert s.answerable_unresolved_rate == pytest.approx(1 / 3)
    assert s.false_answer_rate == pytest.approx(1 / 2)
    assert s.answer_precision == pytest.approx(1 / 3)  # 3 answered, 1 hit
    assert s.answer_recall == pytest.approx(1 / 3)
    assert s.answer_f1 == pytest.approx(1 / 3)


def test_empty_scores_do_not_divide_by_zero() -> None:
    s = score_pairs([])
    assert s.exact_match == 0.0 and s.answer_f1 == 0.0


def test_evaluate_has_every_field_and_overall() -> None:
    golds = [Extraction(lender="A"), Extraction()]
    preds = [Extraction(lender="A"), Extraction(lender="B")]
    scores = evaluate(preds, golds)
    assert set(scores) == {*FIELDS, "overall"}
    assert scores["lender"].exact_match == 0.5
    assert scores["overall"].n == 2 * len(FIELDS)


def test_evaluate_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError):
        evaluate([Extraction()], [])


def test_bootstrap_interval_contains_point_estimate() -> None:
    golds = [Extraction(lender=f"B{i}") for i in range(20)]
    preds = [Extraction(lender=f"B{i}" if i % 2 else "x") for i in range(20)]
    docs = [f"d{i // 2}" for i in range(20)]
    lo, hi = bootstrap_ci(preds, golds, docs, n_boot=200)
    point = evaluate(preds, golds)["overall"].exact_match
    assert lo <= point <= hi
