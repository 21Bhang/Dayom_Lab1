"""Translation adapter interface; connect a vetted model/provider explicitly."""
from __future__ import annotations

from typing import Protocol


class TranslationProvider(Protocol):
    def translate(self, text: str, source_language: str, target_language: str) -> str:
        """Translate text or raise a provider-specific error."""
        ...


def translate_text(text: str, source_language: str, target_language: str,
                   provider: TranslationProvider | None = None) -> str | None:
    """Call an injected provider; return None when translation is not configured."""
    if provider is None:
        return None
    return provider.translate(text, source_language, target_language)
