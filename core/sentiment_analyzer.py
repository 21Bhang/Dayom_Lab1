"""Sentiment adapter boundary for language-specific, human-reviewed models."""
from __future__ import annotations

from typing import Protocol


class SentimentProvider(Protocol):
    def classify(self, text: str, language_code: str) -> dict[str, object]:
        """Return a documented annotation mapping for the supplied language."""
        ...


def analyze_sentiment(text: str, language_code: str,
                      provider: SentimentProvider | None = None) -> dict[str, object]:
    """Avoid fabricating labels: without a vetted provider the result is unknown."""
    if provider is None:
        return {"sentiment": None, "toxicity_score": None, "is_hate_speech": None}
    return provider.classify(text, language_code)
