"""ResponsePresenter: terminal durum satırları ve isteğe bağlı TTS."""

from __future__ import annotations

import sys
from typing import TextIO

from voice_assistant.domain.schemas import ActionResult, ActionStatus
from voice_assistant.ports.protocols import SpeechSynthesizer

STATUS_LABEL: dict[ActionStatus, str] = {
    ActionStatus.SUCCESS: "✔ başarılı",
    ActionStatus.ERROR: "✖ hata",
    ActionStatus.CANCELLED: "↩ iptal",
    ActionStatus.NEEDS_CLARIFICATION: "? açıklama gerekli",
    ActionStatus.NEEDS_CONFIRMATION: "! onay gerekli",
    ActionStatus.UNSUPPORTED: "– desteklenmiyor",
    ActionStatus.UNKNOWN: "? anlaşılamadı",
}


class ConsolePresenter:
    def __init__(self, tts: SpeechSynthesizer | None = None, out: TextIO | None = None) -> None:
        self.tts = tts
        self.out = out or sys.stdout

    def status(self, text: str) -> None:
        print(f"[{text}]", file=self.out, flush=True)

    def show(self, result: ActionResult) -> None:
        label = STATUS_LABEL.get(result.status, result.status.value)
        code = f" ({result.error_code})" if result.error_code else ""
        print(f"[{label}{code}] {result.message}", file=self.out, flush=True)
        if self.tts is not None and self.tts.is_available():
            spoken = self.tts.speak(result.message.splitlines()[0])
            if not spoken and self.tts.name != "console":
                print("[tts: ses üretilemedi, yalnızca metin]", file=self.out, flush=True)
