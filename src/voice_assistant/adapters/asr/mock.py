"""Sabit metin döndüren test ASR'ı."""

from __future__ import annotations

from voice_assistant.domain.schemas import Transcript


class MockRecognizer:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.calls = 0

    @property
    def name(self) -> str:
        return "mock"

    def is_available(self) -> bool:
        return True

    def transcribe(self, clip) -> Transcript:  # type: ignore[no-untyped-def]
        self.calls += 1
        return Transcript(
            text=self.text,
            language="tr",
            duration_s=getattr(clip, "duration_s", None),
            latency_s=0.0,
            provider=self.name,
        )
