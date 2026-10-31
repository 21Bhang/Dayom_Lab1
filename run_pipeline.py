#!/usr/bin/env python3
"""Process JSONL text locally into the Dayom Lab common schema."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

from core.ingestion_pipeline import make_record
from core.sentiment_analyzer import LexiconSentimentProvider, analyze_sentiment


def load_jsonl(path: Path):
    """Yield JSON objects from a UTF-8 JSON Lines file with line-aware errors."""
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: each JSONL row must be an object")
            yield row


def same_file(path_a: Path, path_b: Path) -> bool:
    """Detect identical paths, symlinks, and existing hard links."""
    if path_a.resolve() == path_b.resolve():
        return True
    try:
        return os.path.samefile(path_a, path_b)
    except (FileNotFoundError, OSError):
        return False


def read_config(path: Path, requested_language: str) -> dict[str, Any]:
    if not path.exists():
        return {"language_code": requested_language, "filter_terms": [], "filter_mode": "mask"}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read config {path}: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError(f"config {path} must contain a JSON object")
    configured_language = config.get("language_code", requested_language)
    if configured_language != requested_language:
        raise ValueError(f"config language_code {configured_language!r} does not match --lang {requested_language!r}")
    terms = config.get("filter_terms", [])
    if not isinstance(terms, list) or not all(isinstance(term, str) for term in terms):
        raise ValueError("config field filter_terms must be an array of strings")
    if config.get("filter_mode", "mask") not in {"mask", "exclude", "keep"}:
        raise ValueError("config filter_mode must be mask, exclude, or keep")
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize and filter local text JSONL data.")
    parser.add_argument("--lang", required=True, help="ISO 639-3 language code, e.g. nus")
    parser.add_argument("--input", required=True, type=Path, help="Input JSONL file with text or raw_text")
    parser.add_argument("--output", required=True, type=Path, help="Output JSONL file")
    parser.add_argument("--config", type=Path, help="Language JSON config (defaults to configs/languages/<lang>.json)")
    parser.add_argument("--filter-mode", choices=("mask", "exclude", "keep"), help="Override configured filter mode")
    parser.add_argument("--keep-emoji", action="store_true", help="Do not remove Unicode emoji symbols")
    parser.add_argument("--analyze-sentiment", action="store_true",
                        help="Use the configured lexicon; no labels are produced if it is empty")
    args = parser.parse_args()

    if same_file(args.input, args.output):
        parser.error("--input and --output must refer to different files")

    config_path = args.config or Path("configs/languages") / f"{args.lang}.json"
    try:
        config = read_config(config_path, args.lang)
    except ValueError as exc:
        parser.error(str(exc))
    terms = config["filter_terms"]
    mode = args.filter_mode or config.get("filter_mode", "mask")
    sentiment_provider = None
    if args.analyze_sentiment:
        lexicon = config.get("sentiment_lexicon", {})
        if not isinstance(lexicon, dict):
            parser.error("config field sentiment_lexicon must be a JSON object")
        try:
            sentiment_provider = LexiconSentimentProvider({args.lang: lexicon})
        except ValueError as exc:
            parser.error(str(exc))

    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot create output directory: {exc}", file=sys.stderr)
        return 2

    temporary_path: Path | None = None
    count = excluded = 0
    try:
        # Write beside the destination, then atomically replace it only after all
        # input rows have been read successfully. Existing output survives errors.
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n",
                                         dir=args.output.parent, prefix=f".{args.output.name}.",
                                         suffix=".tmp", delete=False) as out:
            temporary_path = Path(out.name)
            for raw in load_jsonl(args.input):
                record = make_record(raw, language_code=args.lang,
                                     source=str(raw.get("source", "local_file")),
                                     filter_terms=terms, filter_mode=mode,
                                     remove_emoji=not args.keep_emoji)
                if sentiment_provider is not None:
                    predictions = analyze_sentiment(record["cleaned_text"], args.lang, sentiment_provider)
                    for key, value in predictions.items():
                        if record["annotations"].get(key) is None:
                            record["annotations"][key] = value
                excluded += int(record["excluded"])
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
        os.replace(temporary_path, args.output)
        temporary_path = None
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
    print(f"Processed {count} records ({excluded} excluded) -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
