"""Reusable text ingestion and normalization helpers for low-resource languages."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MENTION_RE = re.compile(r"(?<!\w)@[\w.-]+", re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class FilterResult:
    text: str
    matches: tuple[str, ...]


def clean_text(text: str, *, remove_emoji: bool = True) -> str:
    """Normalize Unicode and social-media noise without stripping language letters.

    NFC preserves meaningful orthography such as ä, ö, ɛ and ɔ. Only Unicode
    symbol characters (category So) are removed as emoji; letters and combining
    marks are retained.
    """
    text = unicodedata.normalize("NFC", str(text))
    text = URL_RE.sub(" ", text)
    text = MENTION_RE.sub(" ", text)
    # Keep a hashtag's word, dropping only its marker.
    text = re.sub(r"(?<!\w)#", "", text)
    if remove_emoji:
        text = "".join(ch for ch in text if unicodedata.category(ch) != "So")
    return WHITESPACE_RE.sub(" ", text).strip()


def apply_filter_terms(text: str, terms: Iterable[str], mode: str = "mask") -> FilterResult:
    """Apply a caller-supplied lexicon; never assumes a built-in Nuer word list.

    mode is ``mask`` (replace matched terms), ``exclude`` (return empty text if
    any term matches), or ``keep`` (report matches but leave text unchanged).
    Matching is case-insensitive and whole-term based.
    """
    if mode not in {"mask", "exclude", "keep"}:
        raise ValueError("mode must be one of: mask, exclude, keep")
    normalized_terms = sorted({str(t).strip() for t in terms if str(t).strip()}, key=len, reverse=True)
    matches: list[str] = []
    output = text
    for term in normalized_terms:
        pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE | re.UNICODE)
        found = list(pattern.finditer(output if mode != "mask" else text))
        if found:
            matches.extend([term] * len(found))
            if mode == "mask":
                output = pattern.sub("[FILTERED]", output)
    if mode == "exclude" and matches:
        output = ""
    return FilterResult(text=output, matches=tuple(matches))


def make_record(raw: dict[str, Any], *, language_code: str, source: str = "local_file",
                filter_terms: Iterable[str] = (), filter_mode: str = "mask",
                remove_emoji: bool = True) -> dict[str, Any]:
    """Convert an input object to the shared JSONL record schema."""
    raw_text = str(raw.get("raw_text", raw.get("text", "")))
    cleaned = clean_text(raw_text, remove_emoji=remove_emoji)
    filtered = apply_filter_terms(cleaned, filter_terms, filter_mode)
    original_metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    annotations = raw.get("annotations") if isinstance(raw.get("annotations"), dict) else {}
    metadata = {"source": source, **original_metadata}
    return {
        "id": str(raw.get("id") or ""),
        "language_code": language_code,
        "raw_text": raw_text,
        "cleaned_text": filtered.text,
        "english_translation": raw.get("english_translation"),
        "annotations": {
            "sentiment": annotations.get("sentiment"),
            "toxicity_score": annotations.get("toxicity_score"),
            "is_hate_speech": annotations.get("is_hate_speech"),
        },
        "metadata": metadata,
        "filter_matches": list(filtered.matches),
        "excluded": filter_mode == "exclude" and bool(filtered.matches),
    }
