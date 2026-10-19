"""Testler için mikrofon gerektirmeyen AudioCapture."""

from __future__ import annotations

from voice_assistant.adapters.audio.clip import PcmClip
from voice_assistant.domain.errors import AudioError


class MockAudioCapture:
    def __init__(self, clip: PcmClip | None = None) -> None:
        self._clip = clip
        self._recording = False
        self.closed = False

    def start(self) -> None:
        if self._recording:
            raise AudioError("Kayıt zaten devam ediyor.")
        self._recording = True

    def stop(self) -> PcmClip:
        if not self._recording:
            raise AudioError("Kayıt başlatılmamıştı.")
        self._recording = False
        if self._clip is None:
            raise AudioError("Boş kayıt (mock).")
        return self._clip

    def close(self) -> None:
        self.closed = True
