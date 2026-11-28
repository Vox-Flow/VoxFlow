"""WAV dosyasını ASR'nin beklediği `PcmClip` tipine çevirir.

Mikrofon yakalayıcısının dosya karşılığı: `listen` yolunda `SounddeviceCapture`
ne üretiyorsa, bu da aynısını diskten üretir. Ölçüm betikleri (WER, uçtan uca)
böylece CLI ile aynı girdi tipini kullanır; dönüşüm mantığı betiklere dağılmaz.
"""

from __future__ import annotations

from pathlib import Path

from voice_assistant.adapters.audio.clip import PcmClip
from voice_assistant.domain.errors import AudioError

TARGET_SAMPLE_RATE = 16_000


def load_wav(path: Path | str, *, expected_rate: int = TARGET_SAMPLE_RATE) -> PcmClip:
    """WAV'ı tek kanallı float32 `PcmClip` olarak okur.

    Çok kanallı dosya ortalanarak tek kanala indirilir. Örnekleme hızı
    beklenenden farklıysa yeniden örnekleme **yapılmaz** — sessizce yanlış
    sonuç üretmektense hata verilir; veri hazırlama hattının işi budur.
    """
    try:
        import soundfile as sf
    except ImportError as exc:  # pragma: no cover - ortam kurulumuna bağlı
        raise AudioError("soundfile gerekli: uv sync --extra audio (ya da --extra train)") from exc

    path = Path(path)
    if not path.is_file():
        raise AudioError(f"ses dosyası bulunamadı: {path}")

    audio, sample_rate = sf.read(str(path), dtype="float32")
    if sample_rate != expected_rate:
        raise AudioError(
            f"{path}: örnekleme {sample_rate} Hz, beklenen {expected_rate} Hz. "
            "Dosyayı veri hazırlama betiğiyle dönüştürün."
        )
    if getattr(audio, "ndim", 1) > 1:
        audio = audio.mean(axis=1)
    return PcmClip(audio, sample_rate)
