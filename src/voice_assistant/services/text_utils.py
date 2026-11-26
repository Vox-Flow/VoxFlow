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


def within_one_edit(a: str, b: str) -> bool:
    """İki dize arasındaki Levenshtein uzaklığı en fazla 1 mi (ekleme/silme/değiştirme)?"""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b, strict=True)) == 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    i = 0
    while i < len(short) and short[i] == long_[i]:
        i += 1
    return short[i:] == long_[i + 1 :]


def strip_suffix_apostrophe(token: str) -> str:
    """\"youtube'u\" -> \"youtube\"."""
    return re.split(r"['’]", token, maxsplit=1)[0]
