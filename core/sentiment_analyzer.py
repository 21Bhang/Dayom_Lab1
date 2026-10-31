"""Sentiment adapter boundary and an opt-in, transparent lexicon baseline."""
from __future__ import annotations

import re
from typing import Protocol


class SentimentProvider(Protocol):
    def classify(self, text: str, language_code: str) -> dict[str, object]:
        """Return a documented annotation mapping for the supplied language."""
        ...


class LexiconSentimentProvider:
    """Count supplied positive/negative whole-word terms for one or more languages.

    This intentionally simple baseline is not a trained classifier. Empty or
    unmatched lexicons return unknown sentiment; toxicity and hate-speech remain
    unknown because polarity lexicons cannot establish either label.
    """

    def __init__(self, lexicons: dict[str, dict[str, list[str]]]) -> None:
        self._lexicons: dict[str, tuple[set[str], set[str]]] = {}
        for language, lexicon in lexicons.items():
            if not isinstance(lexicon, dict):
                raise ValueError(f"sentiment lexicon for {language} must be an object")
            positive = lexicon.get("positive", [])
            negative = lexicon.get("negative", [])
            if not isinstance(positive, list) or not all(isinstance(word, str) for word in positive):
                raise ValueError(f"positive sentiment terms for {language} must be an array of strings")
            if not isinstance(negative, list) or not all(isinstance(word, str) for word in negative):
                raise ValueError(f"negative sentiment terms for {language} must be an array of strings")
            self._lexicons[language] = (
                {word.strip().casefold() for word in positive if word.strip()},
                {word.strip().casefold() for word in negative if word.strip()},
            )

    def classify(self, text: str, language_code: str) -> dict[str, object]:
        lexicon = self._lexicons.get(language_code)
        if not lexicon:
            return {"sentiment": None, "toxicity_score": None, "is_hate_speech": None}
        positive, negative = lexicon
        tokens = re.findall(r"\w+", text.casefold(), flags=re.UNICODE)
        positive_hits = sum(token in positive for token in tokens)
        negative_hits = sum(token in negative for token in tokens)
        total_hits = positive_hits + negative_hits
        if total_hits == 0:
            sentiment = None
        elif positive_hits > negative_hits:
            sentiment = "positive"
        elif negative_hits > positive_hits:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        return {
            "sentiment": sentiment,
            "toxicity_score": None,
            "is_hate_speech": None,
        }


def analyze_sentiment(text: str, language_code: str,
                      provider: SentimentProvider | None = None) -> dict[str, object]:
    """Avoid fabricated labels: without a configured provider the result is unknown."""
    if provider is None:
        return {"sentiment": None, "toxicity_score": None, "is_hate_speech": None}
    return provider.classify(text, language_code)
