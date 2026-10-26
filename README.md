# filing-extractor

Pulls five loan terms (facility size, maturity, interest margin, lender, financial covenants) out of public SEC 8-K credit agreement text for ML and data teams, and marks a field `unresolved` when the text does not support it. Personal project on public data.

**Topics:** `information-extraction`, `lora`, `fine-tuning`, `sec-edgar`, `pydantic`, `mlflow`, `fastapi`, `nlp`

![make demo output](docs/demo.png)

## Results

86 held-out test passages from 27 documents. Command: `make eval`. 44% of passages have no answer, so "unresolved" counts as correct in Exact match; read Answer F1 too. Per-field detail, caveats and error analysis: [docs/RESULTS.md](docs/RESULTS.md).

<!-- results:start -->
**Rules (regex)** (86 passages, 27 documents, test split)

| Field | Answerable | Exact match | Answer F1 | EM, answerable only |
|---|---|---|---|---|
| facility_size | 10 | 0.884 | 0.621 | 0.900 |
| maturity | 7 | 0.977 | 0.875 | 1.000 |
| interest_margin | 5 | 0.942 | 0.545 | 0.600 |
| lender | 12 | 0.977 | 0.870 | 0.833 |
| financial_covenants | 5 | 0.953 | 0.500 | 0.400 |
| **overall** | 39 | 0.947 | 0.713 | 0.795 |

Overall exact match 95% interval over documents: 0.926 to 0.966.

**Prompted LLM, structured output**: pending. No `ANTHROPIC_API_KEY` was available, so no numbers are reported. Run `make eval` with a key to fill this in.

**LoRA fine-tuned small model**: pending. Training needs a GPU and has not been run yet; the CPU smoke test only checks that the code runs. Numbers appear here after the GPU run.
<!-- results:end -->

## How it works

```mermaid
flowchart LR
    A[EDGAR full-text search] --> B[download EX-10 exhibits]
    B --> C[pick candidate passages]
    C --> D[hand labels and guidelines]
    D --> E[split by source document]
    E --> F1[rules]
    E --> F2[prompted LLM]
    E --> F3[LoRA fine-tune]
    F1 --> G[grounding check]
    F2 --> G
    F3 --> G
    G --> H[metrics and MLflow]
    G --> I[FastAPI /extract and batch CLI]
```

- `data/passages.jsonl` holds 480 passages from 180 exhibits (sources in `data/sources.csv`), labeled by hand with `docs/LABELING_GUIDELINES.md`. Splits are by document: 126, 27 and 27.
- Three extractors share one interface: regex rules, an LLM forced to call a tool whose schema is the Pydantic model, and Qwen2.5 (0.5B by default, 1.5B in the notebook) fine-tuned with PEFT.
- A grounding check turns any value not found verbatim in the passage into `unresolved`.
- Runs log to MLflow (SQLite in `outputs/`). `/extract` and the batch CLI pick the extractor with `FX_MODEL` or `--model`; the default is `rules`, the only one with measured numbers so far.

## Design choices

1. **Verbatim spans, not normalized values.** I considered numbers and ISO dates and kept spans copied from the text, so labels are machine-checkable and a model cannot invent a value past the grounding check.
2. **`unresolved` is a value.** My first score, 0.93 exact match for the rules on training data, was mostly blank equals blank. I added answer F1 and the answerable-but-unresolved and answered-but-unanswerable rates.
3. **Second labeling pass for rare fields.** A random pass found only 8 interest margin answers in about 490 passages. A targeted second pass and 120 smaller loan papers brought margin to 30, still the thinnest field.
4. **Split and bootstrap by document.** Amendments repeat paragraphs, so a passage split would leak.
5. **Rules first.** They are the number any model has to beat; training errors caught a lender regex that cut "Bank of America, N.A." to "America, N.A.".

## Run it

Python 3.12 or 3.13. No API key, no GPU, no network needed.

```bash
python3 -m venv .venv && . .venv/bin/activate
make install
make demo        # stats, rules baseline on the test split, batch CLI, fake-LLM path, API call
```

More commands:

```bash
make eval        # val and test tables, error analysis, dataset stats (writes results/)
make serve       # API on http://localhost:8000, docs at /docs
curl -s localhost:8000/extract -H 'content-type: application/json' \
  -d '{"text": "...passage text...", "model": "rules"}'
filing-extract --model rules batch data/sample/demo_input.jsonl out.jsonl
```

- **Prompted LLM:** put `ANTHROPIC_API_KEY` in `.env` (see `.env.example`) and run `make eval`. Responses are cached in `results/llm_cache.jsonl`, so reruns cost nothing. Tests and the demo use a fake client with canned answers (`data/sample/`), which prove the plumbing and produce no metric.
- **LoRA smoke test on CPU:** `pip install -r requirements-train.txt && make smoke` (about 30 seconds of training after the 1 GB model download).
- **LoRA on a free GPU:** open `notebooks/train_lora_colab.ipynb` in Colab or Kaggle with a T4. It trains, scores the adapter next to the rules baseline and zips the results. Unzip them in this repo, run `python -m filing_extractor.readme_results`, and commit. The notebook has not been run on a GPU yet. Set `REPO` in the notebook to this repo's URL.
- **Refetch the data:** `scripts/find_exhibits.py` and `scripts/download_exhibits.py` read `SEC_USER_AGENT` (your name and email) from `.env` and stay under 7 requests a second. Passage picking and label merging are in `scripts/`; the labels themselves were written by hand.

## Tests

`make test` runs pytest on the committed data: metric arithmetic against hand-computed values, the grounding check, each regex, the LLM cache and fake client, the API and CLI, label integrity (every label is a verbatim span, no document crosses splits), and a check that the results table above equals what `results/metrics.json` produces. `make lint` runs ruff. CI runs both on Python 3.12 and 3.13.

## What I'd do next

- Label more passages, mainly margins and covenants, and have a second person label a sample to get an agreement score.
- Handle pricing grids as tables instead of flattened text.
- Run the GPU fine-tune on 0.5B and 1.5B, then compare with the LLM baseline on the same test passages.
- Add retrieval so a whole exhibit can be processed, not just a chosen passage.
- Calibrate: let the model say how sure it is, and route low-confidence fields to review.
