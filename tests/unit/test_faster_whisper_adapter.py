"""FasterWhisperRecognizer: model/GPU olmadan hata yolları (sahte WhisperModel ile)."""

import sys
import types

import pytest

np = pytest.importorskip("numpy")

from voice_assistant.adapters.asr.faster_whisper_adapter import FasterWhisperRecognizer  # noqa: E402
from voice_assistant.adapters.audio.clip import PcmClip  # noqa: E402
from voice_assistant.domain.errors import AsrUnavailableError  # noqa: E402


class _Seg:
    def __init__(self, text: str) -> None:
        self.text = text


class _Info:
    language = "tr"
    language_probability = 0.99


def _install_fake(monkeypatch, cls):  # type: ignore[no-untyped-def]
    mod = types.ModuleType("faster_whisper")
    mod.WhisperModel = cls  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "faster_whisper", mod)


def test_gpu_failure_falls_back_to_cpu(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    devices: list[str] = []

    class Fake:
        def __init__(self, size, device, compute_type, download_root, local_files_only):  # type: ignore[no-untyped-def]
            devices.append(device)
            self.device = device

        def transcribe(self, audio, **kw):  # type: ignore[no-untyped-def]
            if self.device != "cpu":
                raise RuntimeError("Library libcublas.so.12 is not found")
            return iter([_Seg(" görev ekle ")]), _Info()

    _install_fake(monkeypatch, Fake)
    r = FasterWhisperRecognizer("base", "auto", "int8")
    assert r.is_available()
    assert devices == ["auto", "cpu"] and r.device == "cpu"
    tr = r.transcribe(PcmClip(np.zeros(16000, dtype="float32"), 16000))
    assert tr.text == "görev ekle" and tr.diagnostics["device"] == "cpu"


def test_model_missing_is_unavailable_not_crash(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class Fake:
        def __init__(self, *a, **k):  # type: ignore[no-untyped-def]
            raise FileNotFoundError("model not in local cache")

    _install_fake(monkeypatch, Fake)
    r = FasterWhisperRecognizer("base", "cpu", "int8")
    assert not r.is_available()
    with pytest.raises(AsrUnavailableError, match="yüklenemedi"):
        r.transcribe(PcmClip(np.zeros(16000, dtype="float32"), 16000))


def test_runtime_error_during_transcribe_is_wrapped(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class Fake:
        calls = 0

        def __init__(self, *a, **k):  # type: ignore[no-untyped-def]
            pass

        def transcribe(self, audio, **kw):  # type: ignore[no-untyped-def]
            Fake.calls += 1
            if Fake.calls == 1:  # ısınma geçer
                return iter([]), _Info()
            raise RuntimeError("CUDA out of memory")

    _install_fake(monkeypatch, Fake)
    r = FasterWhisperRecognizer("base", "cpu", "int8")
    assert r.is_available()
    with pytest.raises(AsrUnavailableError, match="Transkripsiyon başarısız"):
        r.transcribe(PcmClip(np.zeros(16000, dtype="float32"), 16000))


def test_package_missing_message(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    r = FasterWhisperRecognizer("base", "cpu", "int8")
    assert not r.is_available()
    with pytest.raises(AsrUnavailableError, match="kurulu değil"):
        r.transcribe(PcmClip(np.zeros(16000, dtype="float32"), 16000))


def test_initial_prompt_is_passed_to_model(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    seen: dict = {}

    class Fake:
        def __init__(self, *a, **k):  # type: ignore[no-untyped-def]
            pass

        def transcribe(self, audio, **kw):  # type: ignore[no-untyped-def]
            seen.update(kw)
            return iter([_Seg("firefox aç")]), _Info()

    _install_fake(monkeypatch, Fake)
    r = FasterWhisperRecognizer("base", "cpu", "int8", initial_prompt="komutlar: firefox aç")
    tr = r.transcribe(PcmClip(np.zeros(16000, dtype="float32"), 16000))
    assert seen["initial_prompt"] == "komutlar: firefox aç"
    assert seen["task"] == "transcribe" and seen["language"] == "tr"
    assert tr.diagnostics["initial_prompt"] is True


def test_build_asr_prompt_contains_allowlist_names() -> None:
    from voice_assistant.adapters.platforms.launcher import AllowlistLauncher, AppSpec, SiteSpec
    from voice_assistant.wiring import build_asr_prompt

    launcher = AllowlistLauncher(
        {"firefox": AppSpec("firefox", ("firefox", "tarayıcı"), {"linux": ("firefox",)})},
        {"youtube": SiteSpec("youtube", "https://www.youtube.com", ("youtube", "yutup"))},
        platform_name="linux",
        spawn=lambda a: None,
        open_url=lambda u: True,
    )
    p = build_asr_prompt(launcher)
    assert "firefox" in p and "youtube" in p and "görev ekle" in p and len(p) < 800
