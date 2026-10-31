# Dayom Lab

A small, language-agnostic starter for processing text datasets, beginning with Nuer (`nus`). Core logic is separate from per-language JSON configuration so a new language can use the same pipeline without duplicating code.

## Current scope

- Reads **local JSONL** input and writes normalized JSONL output; it does not scrape Facebook, X, or other services.
- Normalizes Unicode to NFC, removes URLs and mentions, collapses whitespace, and removes emoji symbols by default. Nuer letters such as `ä`, `ö`, `ɛ`, and `ɔ` are preserved.
- Applies a configurable, whole-term filter lexicon in `mask`, `exclude`, or `keep` mode. The supplied Nuer and Dinka term lists are intentionally empty: this repository does not invent Nuer vocabulary or classify terms without local review.
- Keeps translation and sentiment as provider interfaces. No translation or sentiment model is bundled, so it does not fabricate these labels.

## Requirements

Python 3.10 or newer. The pipeline uses only the Python standard library; no install step is required.

## Run

Input JSONL records may use either `text` or `raw_text`:

```json
{"id":"example-1","text":"Example text with ä, ö, ɛ, ɔ","metadata":{"source":"local_sample"}}
```

Run from the repository root:

```bash
python3 run_pipeline.py --lang nus --input data/nus/raw/input.jsonl --output data/nus/processed/output.jsonl
```

The default language config is `configs/languages/<lang>.json`. Add reviewed terms to `filter_terms`, or use a separate config with `--config`. Override the configured filter mode with `--filter-mode mask|exclude|keep`. Use `--keep-emoji` to preserve emoji symbols.

Term matching is case-insensitive and whole-term based. `mask` replaces matching terms with `[FILTERED]`; `exclude` sets `cleaned_text` to an empty string and marks the row `excluded: true` (the row remains in output for auditability); `keep` records matches without changing text. Keep filter lexicons private or access-controlled if their contents are sensitive.

## Output schema

Every JSONL output row contains the common fields `id`, `language_code`, `raw_text`, `cleaned_text`, `english_translation`, `annotations`, `metadata`, `filter_matches`, and `excluded`. Unknown translation and annotation values remain `null`. `filter_matches` contains the configured lexicon terms that matched; consider whether that metadata is appropriate before distributing data.

## Add a language

Copy a file under `configs/languages/`, set its ISO 639-3 `language_code`, and add only language resources reviewed by qualified speakers. Then run the same command with `--lang <code>`. No language model weights or datasets are included.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Responsible data handling

Use data only when collection and processing are authorized and consent requirements are met. This starter provides no social-media ingestion, translation model, hate-speech detection, or validated Nuer sentiment system. Human review by fluent speakers is needed before deploying language-specific lexicons or labels. Do not treat toxicity or hate-speech outputs as ground truth without a documented validation process.
