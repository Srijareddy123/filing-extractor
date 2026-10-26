# Labeling guidelines

These are the rules used to label every passage in `data/passages.jsonl`. They were written
before labeling and tightened while labeling; where a rule was added late, earlier labels
were rechecked against it.

## What a passage is

A passage is one paragraph (or two short ones joined) cut from the text of an 8-K exhibit
(EX-10 credit agreements, amendments, loan agreements and notes). It is at most 1,200
characters (mean about 610). Page numbers and document ids that the HTML conversion leaves at the start of a
paragraph are kept as they are, because a model sees the same noise at serving time.

## The five fields

Each field holds either a value copied from the passage or the word `unresolved`.
A value must appear in the passage exactly as written (case and spacing are ignored when
checking). `scripts/merge_labels.py` rejects any label that is not a verbatim span.

| Field | What to copy | Examples |
|---|---|---|
| `facility_size` | The total size of the facility or loan the passage describes. | `$750,000,000`, `€176,000,000` |
| `maturity` | The maturity or final termination date. | `March 25, 2030`, `the fifth anniversary of the Effective Date` |
| `interest_margin` | The spread over a benchmark rate, or the fixed rate when there is no benchmark. | `1.75%`, `12%` |
| `lender` | The lender or the administrative agent, by name. | `JPMORGAN CHASE BANK, N.A.` |
| `financial_covenants` | The first maintenance covenant as `<name> \| <threshold>`. | `Total Net Leverage Ratio \| 4.00 to 1.00` |

### facility_size

- Label the amount of the facility or loan being created, increased or described, including
  the new total in an amendment that sets one, and the principal of a single note.
- Do not label a sublimit (letters of credit, swing line, alternative currency), a minimum
  borrowing amount, a multiple, a fee, a basket, a threshold, a cap on increases, or the
  commitment of one lender out of many.
- Several facilities in one passage: label the first one stated.
- Several draws with no stated total (for example two draws of $250,000,000): `unresolved`.
- Keep the symbol and punctuation as written (`$33,000,000.00`, `US$125,000,000`).

### maturity

- Label the date on which the facility matures or its commitments terminate. A defined
  term such as "Revolving Credit Maturity Date means ... October 24, 2029" counts.
- A relative date counts when no calendar date is given (`the fifth anniversary of ...`).
- Do not label a date that only limits an extension, an availability period, a closing fee
  date, an effective date, or the maturity of other debt (for example a second lien).
- Several maturities (revolver and term loan): the first one stated.
- Dates that depend on a condition with no single current answer: `unresolved`.

### interest_margin

- Label the percentage added to a benchmark (SOFR, LIBOR, prime) for the main loans. When a
  rate has a floor ("greater of SOFR plus 6.65% and 10%"), label the spread.
- A fixed rate counts when the loan has no benchmark (`8.00%`).
- A stated range counts (`0.375% minus 1.75%`).
- Do not label default rates, fees, benchmark adjustments (0.10%), floors, or the Base Rate
  definition (federal funds plus 0.50%). A pricing grid with several levels and no single
  headline number is `unresolved`. A margin that changes with a date or a condition and
  gives more than one value is `unresolved`.

### lender

- Label the administrative agent when one is named ("X, as Administrative Agent").
- Label the lender when the passage names a single lender ("promises to pay to East West
  Bank", "the Lender" defined as a named bank, a signature block headed LENDER).
- Short forms used in the passage count (`JPMCB`, `JPMorgan`).
- Several lenders and no agent, or only "the Lenders": `unresolved`.
- A bank named only as an issuing bank, a syndication agent or an arranger is not enough.

### financial_covenants

- Label a ratio or amount that the borrower must maintain: "shall not permit the Total
  Leverage Ratio to exceed 5.00 to 1.00", "Minimum Fixed Charge Coverage Ratio ... not less
  than 1.20 to 1.00", a minimum net worth or liquidity amount, or a defined maximum ratio.
- Write `<name> | <threshold>`. Both parts are copied from the passage. The name is the
  covenant name as written, without a section number. The threshold is the first number
  stated (the first step of a step-down schedule).
- Several covenants in one passage: the first one.
- A ratio used as a condition for a basket, an investment, a restricted payment, an
  incremental facility or an extension is not a covenant: `unresolved`. So is a definition
  of a ratio without a limit.

## Passages with nothing to extract

Most passages in a credit agreement are boilerplate. About 44% of the 480 passages (213) have no
answer for any field. They are on purpose: a model that fills every field would look good on
only the answerable passages and would invent values everywhere else.

## How passages were picked

1. 130 large credit agreements, amendments and loan agreements were found with EDGAR
   full-text search (8-K, EX-10, 2022 to 2025) and capped at two exhibits per company.
   Another 120 smaller loan agreements and notes were added to cover short documents.
2. For each document the scripts pick paragraphs that mention sizes, dates, rates, ratios or
   lender names (`scripts/make_candidates.py`, `scripts/make_targeted.py`), plus a few random
   paragraphs. The scripts never pre-fill a label.
3. Every picked passage was read and labeled by hand (about 790 in total). Duplicates across
   amendments of the same agreement were dropped.
4. `scripts/build_dataset.py` keeps all passages with an answer and fills the rest of the 480
   with the hardest unanswerable ones (many numbers, dates or party names).
5. The split is by source document: no document has passages in two splits.

## Known limits

- One annotator. There is no agreement score. The checks are the verbatim-span test and a
  review of the disagreements between the rules baseline and the labels on the training split.
- Pricing grids are mostly flattened tables, so margins that sit in grids are `unresolved`
  here. This under-represents a common real case.
- Passage selection favors paragraphs that match the trigger patterns, so the share of
  answerable passages is higher than in a random paragraph sample.
- The test split has 27 documents and 5 to 12 answers per field. Differences of a few
  points between models are inside the noise; the README gives a bootstrap interval.
