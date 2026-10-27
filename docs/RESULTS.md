# Results detail

Test split: 86 labeled passages from 27 documents held out from training and from rule writing. Command: `make eval` (writes `results/`), then `python -m filing_extractor.readme_results` refreshes the tables in this file and in the README.

Exact match counts "unresolved" on an unresolved field as correct, and 44% of passages have no answer, so read the answer-level columns too: Answer F1 looks only at predicted values, "EM, answerable only" only at passages that have an answer.

## Full table

<!-- results:start -->
**Rules (regex)** (86 passages, 27 documents, test split)

| Field | Answerable | Exact match | Answer F1 | EM, answerable only | Unresolved rate | Answerable but unresolved | Answered but unanswerable |
|---|---|---|---|---|---|---|---|
| facility_size | 10 | 0.884 | 0.621 | 0.900 | 0.779 | 0.000 | 0.118 |
| maturity | 7 | 0.977 | 0.875 | 1.000 | 0.895 | 0.000 | 0.025 |
| interest_margin | 5 | 0.942 | 0.545 | 0.600 | 0.930 | 0.400 | 0.037 |
| lender | 12 | 0.977 | 0.870 | 0.833 | 0.872 | 0.083 | 0.000 |
| financial_covenants | 5 | 0.953 | 0.500 | 0.400 | 0.965 | 0.600 | 0.012 |
| **overall** | 39 | 0.947 | 0.713 | 0.795 | 0.888 | 0.154 | 0.038 |

Overall exact match 95% interval over documents: 0.926 to 0.966.

**Prompted LLM, structured output**: pending. No `ANTHROPIC_API_KEY` was available, so no numbers are reported. Run `make eval` with a key to fill this in.

**LoRA fine-tuned small model** (86 passages, 27 documents, test split)

| Field | Answerable | Exact match | Answer F1 | EM, answerable only | Unresolved rate | Answerable but unresolved | Answered but unanswerable |
|---|---|---|---|---|---|---|---|
| facility_size | 10 | 0.860 | 0.581 | 0.900 | 0.756 | 0.000 | 0.145 |
| maturity | 7 | 0.977 | 0.875 | 1.000 | 0.895 | 0.000 | 0.025 |
| interest_margin | 5 | 0.942 | 0.444 | 0.400 | 0.953 | 0.600 | 0.025 |
| lender | 12 | 0.942 | 0.815 | 0.917 | 0.826 | 0.083 | 0.054 |
| financial_covenants | 5 | 0.988 | 0.909 | 1.000 | 0.930 | 0.000 | 0.012 |
| **overall** | 39 | 0.942 | 0.723 | 0.872 | 0.872 | 0.103 | 0.051 |

Overall exact match 95% interval over documents: 0.915 to 0.966.
<!-- results:end -->

## Notes

- **The prompted LLM row is pending on purpose.** No Anthropic key was available, so no number is shown until a run produces one.
- **The LoRA row comes from one Colab T4 run.** The model size (0.5B is the notebook default, 1.5B is an option) was not recorded in `results/`. The 33 MB adapter is not in the repo and is available on request.
- The CPU smoke test (`make smoke`, `results/smoke_train_summary.json`) trains 6 steps on 12 passages to check that the training and inference code runs. Its loss went from 0.793 to 0.033 in 28 seconds. That says nothing about quality.
- The test split has 5 to 12 answers per field. A difference of a few points between two models is inside the noise; the interval above resamples whole documents.
- Rules were written after reading the training and validation errors. I also labeled the test passages, so the rules row is mildly optimistic.

**Error analysis** (rules, validation and test, 48 wrong pairs out of 830; `results/error_analysis_rules.md` has every count and more examples):

1. Facility size, answered but unanswerable (18). The regex finds a dollar amount near the word "commitment" and takes it, but it is a sublimit, a participation threshold or a letter of credit commitment, not the facility (`fx0012`: "LC Commitment means ... $50,000,000").
2. Interest margin, answered but unanswerable (6). It reads a percentage from a Base Rate definition or a fee, such as "Term SOFR plus 1.00%" inside a definition (`fx0032`).
3. Maturity, answered but unanswerable (6). Any date after the word "Termination Date" is taken, even when it is the start of an interest payment schedule (`fx0057`, "commencing June 30, 2024").

Missed answers (11) sit mostly in interest margin and financial covenants, where the wording varies the most. Rules against LoRA on the test split (answer F1, from `results/results.md`):

- **Overall:** LoRA 0.723 against rules 0.713. Answer recall is 0.872 against 0.795 (34 against 31 of 39 answerable fields), precision 0.618 against 0.646, false answers 5.1% against 3.8%, exact match 0.942 against 0.947. On validation LoRA is slightly behind (answer F1 0.735 against 0.740, recall 0.837 against 0.860). The 95% intervals for exact match overlap (0.915 to 0.966 and 0.926 to 0.966), so this is not a clear win.
- **By field (test):** LoRA is much better on financial covenants (answer F1 0.909 against 0.500, 5 answerable). It is worse on facility size (0.581 against 0.621), interest margin (0.444 against 0.545) and lender (0.815 against 0.870); maturity is level (0.875).
- **By document kind (test):** LoRA is better on long agreements (0.788 against 0.730, 28 answerable) and worse on short loan papers (0.571 against 0.667, 11 answerable).
- **LoRA failures** (`results/error_analysis_lora.md`, validation and test, 47 wrong pairs out of 830): 35 are false answers where the label is unresolved, mostly facility size (17: it takes a sublimit or basket amount, such as the LC commitment in `fx0012`) and lender (7); 7 are missed answers, 5 of them interest margin.

## Background moved from the README

Personal project on public data. Sources are in `data/sources.csv`; labeling rules are in `docs/LABELING_GUIDELINES.md`.

Fuller flow: EDGAR full-text search, download EX-10 exhibits, pick candidate passages, hand labels, split by source document, then rules, prompted LLM or LoRA fine-tune, grounding check, metrics and MLflow, FastAPI `/extract` and batch CLI.

- Qwen2.5 is 0.5B by default and 1.5B in the notebook. MLflow uses SQLite in `outputs/`.
- Score history: my first score, 0.93 exact match for the rules on training data, was mostly blank equals blank. I added answer F1 and the answerable-but-unresolved and answered-but-unanswerable rates.
- Margin coverage: a targeted second labeling pass plus 120 smaller loan papers brought interest margin to 30 answers.
- Rules: training errors caught a lender regex that cut "Bank of America, N.A." to "America, N.A.".
