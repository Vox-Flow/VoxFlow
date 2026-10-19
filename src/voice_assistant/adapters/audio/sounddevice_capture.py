"""sounddevice ile 16 kHz mono mikrofon kaydı (Faz 2 iskeleti).

Neden 16 kHz mono: Whisper ailesi 16 kHz mono bekler; daha yüksek örnekleme
yalnızca yeniden örnekleme maliyeti getirir. Ses yalnızca RAM'de tutulur.
"""

from __future__ import annotations

import logging
import threading

from voice_assistant.adapters.audio.clip import PcmClip
from voice_assistant.domain.errors import AudioError

log = logging.getLogger("voxflow.audio")


class SounddeviceCapture:
    def __init__(self, sample_rate: int = 16000, channels: int = 1, max_seconds: int = 60) -> None:
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise AudioError(
                "Ses kaydı için 'sounddevice' ve 'numpy' gerekli: pip install 'voxflow[audio]'"
            ) from exc
        self._np = np
        self._sd = sd
        self.sample_rate = sample_rate
        self.channels = channels
        self.max_seconds = max_seconds
        self._frames: list[object] = []
        self._stream = None
        self._lock = threading.Lock()
        self._overflow = False

    def _callback(self, indata, frames, time, status) -> None:  # type: ignore[no-untyped-def]
        if status:
            self._overflow = True
        with self._lock:
            total = sum(len(f) for f in self._frames)  # type: ignore[arg-type]
            if total < self.max_seconds * self.sample_rate:
                self._frames.append(indata.copy())

    def start(self) -> None:
        if self._stream is not None:
            raise AudioError("Kayıt zaten devam ediyor.")
        self._frames = []
        self._overflow = False
        try:
            self._stream = self._sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()
        except Exception as exc:  # noqa: BLE001 - PortAudio hataları çeşitli tiplerde gelir
            self._stream = None
            raise AudioError(f"Mikrofon açılamadı: {exc}") from exc

    def stop(self) -> PcmClip:
        if self._stream is None:
            raise AudioError("Kayıt başlatılmamıştı.")
        try:
            self._stream.stop()
            self._stream.close()
        finally:
            self._stream = None
        with self._lock:
            frames = self._frames
            self._frames = []
        if not frames:
            raise AudioError("Boş kayıt: hiç ses örneği alınamadı.")
        audio = self._np.concatenate(frames, axis=0)
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        audio = audio.astype("float32")
        rms = float(self._np.sqrt(self._np.mean(audio**2))) if len(audio) else 0.0
        if rms < 1e-4:
            raise AudioError("Kayıt sessiz görünüyor (RMS çok düşük). Mikrofon kapalı olabilir.")
        if self._overflow:
            log.warning("Kayıt sırasında tampon taşması bildirildi; kalite düşmüş olabilir.")
        return PcmClip(samples=audio, sample_rate=self.sample_rate)

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None
        self._frames = []
