"""Score the extractors on the labeled passages and write tables, predictions and MLflow runs."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from filing_extractor.config import OUTPUT_DIR, ROOT
from filing_extractor.data import Passage, load_doc_kinds, load_passages
from filing_extractor.llm import CacheMiss
from filing_extractor.metrics import FieldScores, bootstrap_ci, evaluate
from filing_extractor.prompt import SYSTEM_PROMPT, build_user_prompt
from filing_extractor.registry import (
    LLM_CACHE,
    Extractor,
    ModelUnavailable,
    get_extractor,
    llm_cached_client,
)
from filing_extractor.schema import FIELDS, Extraction

RESULTS_DIR = ROOT / "results"
EXPERIMENT = "filing-extractor"
COLUMNS = (
    ("Field", None),
    ("Answerable", "n_answerable"),
    ("Exact match", "exact_match"),
    ("F1", "f1"),
    ("Answer precision", "answer_precision"),
    ("Answer recall", "answer_recall"),
    ("Answer F1", "answer_f1"),
    ("EM, answerable only", "exact_match_answerable"),
    ("Unresolved rate", "unresolved_rate"),
    ("Answerable but unresolved", "answerable_unresolved_rate"),
    ("Answered but unanswerable", "false_answer_rate"),
)


def predict(extractor: Extractor, passages: list[Passage]) -> list[Extraction]:
    return [extractor.extract(p.text) for p in passages]


def llm_pending_reason(passages: list[Passage]) -> str | None:
    """None when the LLM baseline can run (key set, or every response already cached)."""
    client = llm_cached_client()
    if client._inner is not None:  # live client available
        return None
    missing = sum(not client.has(SYSTEM_PROMPT, build_user_prompt(p.text)) for p in passages)
    if missing == 0:
        return None
    return (
        f"pending: ANTHROPIC_API_KEY is not set and {missing} of {len(passages)} responses "
        f"are not cached in {LLM_CACHE.relative_to(ROOT)}"
    )


def markdown_table(scores: dict[str, FieldScores]) -> str:
    head = "| " + " | ".join(name for name, _ in COLUMNS) + " |"
    rule = "|" + "|".join("---" for _ in COLUMNS) + "|"
    lines = [head, rule]
    for field in (*FIELDS, "overall"):
        s = scores[field].as_dict()
        cells = [f"**{field}**" if field == "overall" else field]
        for _, key in COLUMNS[1:]:
            cells.append(str(s[key]) if key == "n_answerable" else f"{s[key]:.3f}")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def run(
    models: list[str],
    splits: list[str],
    out_dir: Path,
    adapter: Path | None,
    use_mlflow: bool,
) -> dict:
    result: dict = {"splits": {}, "status": {}}
    sections: list[str] = []
    for model in models:
        extractor, reason = _load(model, adapter, splits)
        result["status"][model] = reason or "ok"
        if extractor is None:
            sections.append(f"### {model}\n\nNot run. {reason}.\n")
            continue
        for split in splits:
            passages = load_passages(split=split)
            started = time.time()
            preds = predict(extractor, passages)
            seconds = time.time() - started
            golds = [p.gold for p in passages]
            scores = evaluate(preds, golds)
            lo, hi = bootstrap_ci(preds, golds, [p.doc_id for p in passages])
            result["splits"].setdefault(split, {})[model] = {
                "n_passages": len(passages),
                "n_documents": len({p.doc_id for p in passages}),
                "overall_exact_match_ci95": [round(lo, 3), round(hi, 3)],
                "seconds": round(seconds, 2),
                "parse_errors": getattr(extractor, "parse_errors", 0),
                "fields": {k: v.as_dict() for k, v in scores.items()},
                "by_doc_kind": _by_doc_kind(passages, preds),
            }
            _write_predictions(out_dir, model, split, passages, preds)
            sections.append(
                f"### {model}, {split} split "
                f"({len(passages)} passages from {len({p.doc_id for p in passages})} documents)\n\n"
                f"{markdown_table(scores)}\n\n"
                f"Overall exact match 95% interval (bootstrap over documents): "
                f"{lo:.3f} to {hi:.3f}.\n\n"
                f"{_doc_kind_table(result['splits'][split][model]['by_doc_kind'])}\n"
            )
            if use_mlflow:
                _log_mlflow(
                    model, split, scores, len(passages), seconds, getattr(extractor, "name", model)
                )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (out_dir / "results.md").write_text("\n".join(sections), encoding="utf-8")
    return result


def _by_doc_kind(passages: list[Passage], preds: list[Extraction]) -> dict[str, dict]:
    """Overall scores for long agreements and for short amendments and loan papers."""
    kinds = load_doc_kinds()
    out: dict[str, dict] = {}
    for kind in ("long", "short"):
        keep = [i for i, p in enumerate(passages) if kinds[p.doc_id] == kind]
        if not keep:
            continue
        scores = evaluate([preds[i] for i in keep], [passages[i].gold for i in keep])["overall"]
        out[kind] = {"n_passages": len(keep)} | scores.as_dict()
    return out


def _doc_kind_table(by_kind: dict[str, dict]) -> str:
    lines = [
        "| Document kind | Passages | Answerable | Answer F1 | EM, answerable only "
        "| Answerable but unresolved | Answered but unanswerable |",
        "|---|---|---|---|---|---|---|",
    ]
    for kind, s in by_kind.items():
        lines.append(
            f"| {kind} | {s['n_passages']} | {s['n_answerable']} | {s['answer_f1']:.3f} | "
            f"{s['exact_match_answerable']:.3f} | {s['answerable_unresolved_rate']:.3f} | "
            f"{s['false_answer_rate']:.3f} |"
        )
    return "\n".join(lines)


def _load(
    model: str, adapter: Path | None, splits: list[str]
) -> tuple[Extractor | None, str | None]:
    if model == "llm":
        passages = [p for s in splits for p in load_passages(split=s)]
        reason = llm_pending_reason(passages)
        if reason:
            return None, reason
    try:
        return get_extractor(model, adapter), None
    except ModelUnavailable as exc:
        return None, f"pending: {exc}"
    except CacheMiss as exc:
        return None, f"pending: {exc}"


def _write_predictions(
    out_dir: Path, model: str, split: str, passages: list[Passage], preds: list[Extraction]
) -> None:
    folder = out_dir / "predictions"
    folder.mkdir(parents=True, exist_ok=True)
    rows = [{"id": p.id, "pred": pred.as_dict()} for p, pred in zip(passages, preds, strict=True)]
    (folder / f"{model}_{split}.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )


def _log_mlflow(
    model: str, split: str, scores: dict[str, FieldScores], n: int, seconds: float, name: str
) -> None:
    import mlflow

    db = OUTPUT_DIR / "mlflow.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{db}")
    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run(run_name=f"eval-{model}-{split}"):
        mlflow.log_params({"kind": "eval", "model": name, "split": split, "n_passages": n})
        mlflow.log_metric("seconds", seconds)
        for field, s in scores.items():
            mlflow.log_metrics(
                {
                    f"{field}.exact_match": s.exact_match,
                    f"{field}.f1": s.f1,
                    f"{field}.unresolved_rate": s.unresolved_rate,
                    f"{field}.answerable_unresolved_rate": s.answerable_unresolved_rate,
                }
            )


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--models", nargs="+", default=["rules", "llm", "lora"])
    p.add_argument("--splits", nargs="+", default=["val", "test"])
    p.add_argument("--out", type=Path, default=RESULTS_DIR)
    p.add_argument("--lora-adapter", type=Path, default=None)
    p.add_argument("--no-mlflow", action="store_true")
    args = p.parse_args(argv)
    result = run(args.models, args.splits, args.out, args.lora_adapter, not args.no_mlflow)
    print((args.out / "results.md").read_text(encoding="utf-8"))
    for model, status in result["status"].items():
        if status != "ok":
            print(f"[{model}] {status}")


if __name__ == "__main__":
    main()
