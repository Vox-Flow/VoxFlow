"""rich tabanlı terminal sunumu. GUI değil; yalnızca aynı terminalin renkli hâli.

`rich` isteğe bağlıdır (`uv sync --extra ui`); kurulu değilse bu modül hiç
yüklenmez ve `build_presenter` düz metin adaptörüne düşer.
"""

from __future__ import annotations

import sys
from typing import TextIO

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from voice_assistant.adapters.ui.common import (
    TTS_FAILED_NOTE,
    label_for,
    speak_and_needs_note,
    style_for,
)
from voice_assistant.domain.schemas import ActionResult
from voice_assistant.ports.protocols import SpeechSynthesizer


class RichPresenter:
    """ResponsePresenter: durumu renkli başlıkla, mesajı çerçeve içinde gösterir."""

    def __init__(
        self,
        tts: SpeechSynthesizer | None = None,
        out: TextIO | None = None,
        width: int | None = None,
    ) -> None:
        self.tts = tts
        self.console = Console(file=out or sys.stdout, width=width, highlight=False)

    @property
    def name(self) -> str:
        return "rich"

    def status(self, text: str) -> None:
        # Text(): mesaj içindeki köşeli parantezler rich biçimlendirmesi sayılmasın.
        self.console.print(Text(f"[{text}]", style="dim"))

    def show(self, result: ActionResult) -> None:
        style = style_for(result.status)
        code = f" ({result.error_code})" if result.error_code else ""
        self.console.print(
            Panel(
                Text(result.message),
                title=Text(f"{label_for(result.status)}{code}", style=style),
                title_align="left",
                border_style=style,
                padding=(0, 1),
            )
        )
        if speak_and_needs_note(self.tts, result.message):
            self.console.print(Text(TTS_FAILED_NOTE, style="dim"))
