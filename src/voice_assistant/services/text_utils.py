"""Türkçe metin normalizasyonu için küçük yardımcılar."""

from __future__ import annotations

import re
import unicodedata

_PUNCT_RE = re.compile(r"[^\w\s'’]", re.UNICODE)
_WS_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Küçük harf (Türkçe İ/I farkına dikkat ederek), noktalama ve fazla boşluk temizliği."""
    text = text.replace("I", "ı").replace("İ", "i")
    text = text.lower()
    text = unicodedata.normalize("NFC", text)
    text = _PUNCT_RE.sub(" ", text)
    return _WS_RE.sub(" ", text).strip()


def strip_suffix_apostrophe(token: str) -> str:
    """\"youtube'u\" -> \"youtube\"."""
    return re.split(r"['’]", token, maxsplit=1)[0]
