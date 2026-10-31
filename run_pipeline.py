#!/usr/bin/env python3
"""Process JSONL text locally into the Dayom Lab common schema."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from core.ingestion_pipeline import make_record


def load_jsonl(path: Path):
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize and filter local text JSONL data.")
    parser.add_argument("--lang", required=True, help="ISO 639-3 language code, e.g. nus")
    parser.add_argument("--input", required=True, type=Path, help="Input JSONL file with text or raw_text")
    parser.add_argument("--output", required=True, type=Path, help="Output JSONL file")
    parser.add_argument("--config", type=Path, help="Language JSON config (defaults to configs/languages/<lang>.json)")
    parser.add_argument("--filter-mode", choices=("mask", "exclude", "keep"), help="Override configured filter mode")
    parser.add_argument("--keep-emoji", action="store_true", help="Do not remove Unicode emoji symbols")
    args = parser.parse_args()

    config_path = args.config or Path("configs/languages") / f"{args.lang}.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        config = {"language_code": args.lang, "filter_terms": [], "filter_mode": "mask"}
    lang = str(config.get("language_code", args.lang))
    terms = config.get("filter_terms", [])
    mode = args.filter_mode or config.get("filter_mode", "mask")
    if not isinstance(terms, list):
        parser.error("config field filter_terms must be a JSON array")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = excluded = 0
    try:
        with args.output.open("w", encoding="utf-8", newline="\n") as out:
            for raw in load_jsonl(args.input):
                record = make_record(raw, language_code=lang, source=str(raw.get("source", "local_file")),
                                    filter_terms=terms, filter_mode=mode, remove_emoji=not args.keep_emoji)
                excluded += int(record["excluded"])
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Processed {count} records ({excluded} excluded) -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
