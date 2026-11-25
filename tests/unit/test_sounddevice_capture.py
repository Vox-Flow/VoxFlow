"""SounddeviceCapture'ın mikrofon gerektirmeyen mantık testleri (stop sonrası kontroller)."""

import logging

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("sounddevice")

from voice_assistant.adapters.audio.sounddevice_capture import SounddeviceCapture  # noqa: E402
from voice_assistant.domain.errors import AudioError  # noqa: E402


class _FakeStream:
    def stop(self) -> None: ...
    def close(self) -> None: ...


def _capture_with(frames):  # type: ignore[no-untyped-def]
    c = SounddeviceCapture(16000, 1, 60)
    c._stream = _FakeStream()  # gerçek PortAudio akışı açılmaz
    c._frames = [np.asarray(f, dtype="float32").reshape(-1, 1) for f in frames]
    return c


def test_too_short_recording_is_error() -> None:
    c = _capture_with([np.zeros(800) + 0.1])  # 0.05 sn
    with pytest.raises(AudioError, match="çok kısa"):
        c.stop()


def test_silent_recording_is_error() -> None:
    c = _capture_with([np.zeros(16000)])  # 1 sn sessizlik
    with pytest.raises(AudioError, match="sessiz"):
        c.stop()


def test_no_frames_is_error() -> None:
    c = _capture_with([])
    with pytest.raises(AudioError, match="Boş kayıt"):
        c.stop()


def test_normal_recording_returns_mono_clip() -> None:
    t = np.arange(16000) / 16000
    c = _capture_with([0.3 * np.sin(2 * np.pi * 440 * t)])
    clip = c.stop()
    assert clip.sample_rate == 16000 and abs(clip.duration_s - 1.0) < 1e-6
    assert clip.to_float32().ndim == 1


def test_clipping_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    c = _capture_with([np.ones(16000)])  # tam ölçek
    with caplog.at_level(logging.WARNING, logger="voxflow.audio"):
        c.stop()
    assert any("kırpılma" in r.message for r in caplog.records)


def test_stop_before_start_and_double_start() -> None:
    c = SounddeviceCapture()
    with pytest.raises(AudioError):
        c.stop()
