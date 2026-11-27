"""`load_wav`: diskteki WAV → ASR'nin beklediği `PcmClip`.

Ölçüm betikleri bu yardımcıyı kullanır; davranışı mikrofon yolundakiyle aynı
olmalı, aksi hâlde WER ile canlı kullanım farklı girdi görür.
"""

from pathlib import Path

import pytest

sf = pytest.importorskip("soundfile", reason="soundfile yalnızca audio/train ekstralarında")
np = pytest.importorskip("numpy")

from voice_assistant.adapters.audio.wav_file import load_wav  # noqa: E402
from voice_assistant.domain.errors import AudioError  # noqa: E402

RATE = 16_000


def _wav(path: Path, seconds: float = 0.5, channels: int = 1, rate: int = RATE) -> Path:
    shape = (int(rate * seconds),) if channels == 1 else (int(rate * seconds), channels)
    sf.write(str(path), np.zeros(shape, dtype="float32"), rate, subtype="PCM_16")
    return path


def test_returns_pcm_clip_with_expected_shape(tmp_path: Path) -> None:
    clip = load_wav(_wav(tmp_path / "a.wav", 0.5))
    assert clip.sample_rate == RATE
    assert clip.duration_s == pytest.approx(0.5)
    assert clip.to_float32().dtype == np.float32
    assert clip.to_float32().ndim == 1


def test_multichannel_is_mixed_down(tmp_path: Path) -> None:
    clip = load_wav(_wav(tmp_path / "s.wav", 0.25, channels=2))
    assert clip.to_float32().ndim == 1
    assert clip.duration_s == pytest.approx(0.25)


def test_wrong_sample_rate_raises_instead_of_resampling(tmp_path: Path) -> None:
    """Sessizce yeniden örneklemek yanlış WER üretir; hata vermek doğrusu."""
    with pytest.raises(AudioError) as exc:
        load_wav(_wav(tmp_path / "b.wav", 0.2, rate=8000))
    assert "8000" in str(exc.value)
    assert exc.value.code == "E_AUDIO"


def test_missing_file_raises_audio_error(tmp_path: Path) -> None:
    with pytest.raises(AudioError):
        load_wav(tmp_path / "yok.wav")


def test_float_wav_is_accepted(tmp_path: Path) -> None:
    """FLEURS 32 bit float dağıtıyor; okuyucu bunu da kabul etmeli."""
    path = tmp_path / "f.wav"
    sf.write(str(path), np.zeros(RATE // 2, dtype="float32"), RATE, subtype="FLOAT")
    assert load_wav(path).duration_s == pytest.approx(0.5)
