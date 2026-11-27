"""Sunum adaptörleri ve seçim mantığı (ResponsePresenter portu)."""

from __future__ import annotations

import sys
from typing import TextIO

from voice_assistant.adapters.ui.console import ConsolePresenter
from voice_assistant.ports.protocols import ResponsePresenter, SpeechSynthesizer

UI_CHOICES = ("auto", "plain", "rich")

__all__ = ["UI_CHOICES", "ConsolePresenter", "build_presenter"]


def _is_tty(stream: TextIO) -> bool:
    try:
        return bool(stream.isatty())
    except (ValueError, AttributeError):  # kapalı ya da dosya benzeri akış
        return False


def build_presenter(
    kind: str = "auto",
    tts: SpeechSynthesizer | None = None,
    out: TextIO | None = None,
    warnings: list[str] | None = None,
) -> ResponsePresenter:
    """Sunum adaptörünü seçer.

    `auto`: terminalde rich (kuruluysa), boruya/dosyaya yazarken düz metin —
    böylece `voxflow ... > out.txt` ve testler kaçış kodu içermez.
    `rich` istenip kurulu değilse sessizce düşmek yerine uyarı eklenir.
    """
    stream = out or sys.stdout
    if kind == "plain":
        return ConsolePresenter(tts, stream)
    if kind == "auto" and not _is_tty(stream):
        return ConsolePresenter(tts, stream)
    try:
        from voice_assistant.adapters.ui.rich_ui import RichPresenter
    except ImportError:
        if kind == "rich" and warnings is not None:
            warnings.append(
                "rich kurulu değil (uv sync --extra ui); düz metin arayüz kullanılıyor."
            )
        return ConsolePresenter(tts, stream)
    return RichPresenter(tts, stream)
