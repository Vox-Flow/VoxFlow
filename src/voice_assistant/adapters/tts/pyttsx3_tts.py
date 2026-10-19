"""İsteğe bağlı yerel TTS (pyttsx3 -> espeak/sapi5/nsss). Paket yoksa kullanılamaz."""

from __future__ import annotations

import logging

log = logging.getLogger("voxflow.tts")


class Pyttsx3Synthesizer:
    def __init__(self) -> None:
        self._engine = None
        try:
            import pyttsx3  # type: ignore[import-not-found]

            self._engine = pyttsx3.init()
        except Exception as exc:  # noqa: BLE001 - sürücü yoksa sessiz fallback
            log.info("pyttsx3 başlatılamadı, sessiz fallback: %s", exc)

    @property
    def name(self) -> str:
        return "pyttsx3"

    def is_available(self) -> bool:
        return self._engine is not None

    def speak(self, text: str) -> bool:
        if self._engine is None:
            return False
        try:
            self._engine.say(text)
            self._engine.runAndWait()
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("TTS hatası: %s", exc)
            return False
