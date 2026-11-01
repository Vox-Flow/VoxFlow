"""faster-whisper tabanlı yerel ASR (Faz 2 iskeleti).

- language="tr", task="transcribe": çeviri yapılmaz.
- Model dosyaları önceden indirilmiş olmalı (bkz. docs/setup.md, çevrimdışı mod).
- Paket/model yoksa uygulama çökmez; AsrUnavailableError ile anlaşılır uyarı verir.
"""

from __future__ import annotations

import logging
import time

from voice_assistant.domain.errors import AsrUnavailableError
from voice_assistant.domain.schemas import Transcript

log = logging.getLogger("voxflow.asr")


class FasterWhisperRecognizer:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
        download_root: str | None = None,
        local_files_only: bool = True,
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._download_root = download_root
        self._local_only = local_files_only
        self._model = None
        self._error: str | None = None

    @property
    def name(self) -> str:
        return f"faster-whisper:{self.model_size}"

    def _load(self) -> None:
        if self._model is not None or self._error is not None:
            return
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]
        except ImportError:
            self._error = "faster-whisper kurulu değil: pip install 'voxflow[asr]'"
            return
        try:
            self._model = self._load_on(WhisperModel, self.device, self.compute_type)
            self._warm_up()
        except Exception as exc:  # noqa: BLE001
            if self.device != "cpu":
                # GPU kütüphanesi eksik/bozuk (örn. libcublas bulunamadı): CPU'ya düş.
                log.warning("GPU ile ASR başlatılamadı (%s); CPU'ya geçiliyor.", exc)
                try:
                    self.device, self.compute_type = "cpu", "int8"
                    self._model = self._load_on(WhisperModel, "cpu", "int8")
                    self._warm_up()
                    return
                except Exception as exc2:  # noqa: BLE001
                    exc = exc2
            self._model = None
            self._error = (
                f"Whisper modeli yüklenemedi ({self.model_size}). "
                "Model önceden indirilmemiş olabilir; "
                f"bkz. docs/setup.md. Ayrıntı: {exc}"
            )

    def _load_on(self, cls, device: str, compute_type: str):  # type: ignore[no-untyped-def]
        return cls(
            self.model_size,
            device=device,
            compute_type=compute_type,
            download_root=self._download_root,
            local_files_only=self._local_only,
        )

    def _warm_up(self) -> None:
        """Kısa sessizlikle çalıştırıp CUDA çalışma zamanı hatalarını yüklemede yakalar."""
        import numpy as np

        assert self._model is not None
        segments, _ = self._model.transcribe(
            np.zeros(1600, dtype="float32"), language="tr", task="transcribe", beam_size=1
        )
        list(segments)

    def is_available(self) -> bool:
        self._load()
        return self._model is not None

    def transcribe(self, clip) -> Transcript:  # type: ignore[no-untyped-def]
        self._load()
        if self._model is None:
            raise AsrUnavailableError(self._error or "ASR kullanılamıyor.")
        audio = clip.to_float32()
        t0 = time.perf_counter()
        try:
            segments, info = self._model.transcribe(
                audio, language="tr", task="transcribe", beam_size=5, vad_filter=True
            )
            text = " ".join(s.text.strip() for s in segments).strip()
        except Exception as exc:  # noqa: BLE001 - CTranslate2/CUDA hataları çeşitli tiplerde
            raise AsrUnavailableError(
                f"Transkripsiyon başarısız ({type(exc).__name__}: {exc}). "
                'GPU kütüphaneleri eksikse config/app.json içinde asr.device = "cpu" deneyin.'
            ) from exc
        latency = time.perf_counter() - t0
        return Transcript(
            text=text,
            language=info.language,
            duration_s=clip.duration_s,
            latency_s=latency,
            provider=self.name,
            diagnostics={
                "language_probability": getattr(info, "language_probability", None),
                "device": self.device,
                "compute_type": self.compute_type,
            },
        )
