PY ?= python

.PHONY: install demo test lint eval smoke serve data-stats

install:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e . --no-deps

demo:
	$(PY) scripts/demo.py

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .

# Scores val and test, writes results/, then the error analysis and dataset table.
# The llm and lora rows say "pending" until a key is set or an adapter exists.
eval:
	$(PY) -m filing_extractor.evaluate --splits val test
	$(PY) -m filing_extractor.errors --model rules --splits val test
	$(PY) -m filing_extractor.stats

# A few optimizer steps of the LoRA fine-tune on CPU (needs requirements-train.txt).
smoke:
	$(PY) -m filing_extractor.train_lora --smoke

serve:
	$(PY) -m uvicorn filing_extractor.api:app --port 8000
