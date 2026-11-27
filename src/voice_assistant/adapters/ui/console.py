"""Düz metin terminal sunumu. Bağımlılık gerektirmez; testlerin referans çıktısı budur."""

from __future__ import annotations

import sys
from typing import TextIO

from voice_assistant.adapters.ui.common import (
    TTS_FAILED_NOTE,
    label_for,
    speak_and_needs_note,
)
from voice_assistant.domain.schemas import ActionResult
from voice_assistant.ports.protocols import SpeechSynthesizer


class ConsolePresenter:
    """ResponsePresenter: durum satırları + isteğe bağlı TTS."""

    def __init__(self, tts: SpeechSynthesizer | None = None, out: TextIO | None = None) -> None:
        self.tts = tts
        self.out = out or sys.stdout

    @property
    def name(self) -> str:
        return "plain"

    def status(self, text: str) -> None:
        print(f"[{text}]", file=self.out, flush=True)

    def show(self, result: ActionResult) -> None:
        label = label_for(result.status)
        code = f" ({result.error_code})" if result.error_code else ""
        print(f"[{label}{code}] {result.message}", file=self.out, flush=True)
        if speak_and_needs_note(self.tts, result.message):
            print(TTS_FAILED_NOTE, file=self.out, flush=True)
