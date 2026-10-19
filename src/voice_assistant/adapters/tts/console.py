"""Sessiz fallback TTS: hiçbir ses üretmez, bunu açıkça bildirir."""

from __future__ import annotations


class ConsoleSynthesizer:
    @property
    def name(self) -> str:
        return "console"

    def is_available(self) -> bool:
        return True

    def speak(self, text: str) -> bool:
        return False  # ses üretilmedi; metin zaten terminalde gösteriliyor
