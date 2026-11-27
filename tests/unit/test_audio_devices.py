"""Giriş aygıtı listeleme ve seçme (#59).

Gerçek ses donanımı gerektirmez: `sounddevice` sahte bir modülle değiştirilir,
böylece CI'da ve mikrofonsuz makinelerde de koşar.
"""

import sys
import types

import pytest

from voice_assistant.adapters.audio import devices as dev
from voice_assistant.domain.errors import AudioError

AYGITLAR = [
    {"name": "Loopback", "max_input_channels": 2, "default_samplerate": 44100.0, "hostapi": 0},
    {"name": "Hoparlör", "max_input_channels": 0, "default_samplerate": 48000.0, "hostapi": 0},
    {
        "name": "Realtek Mikrofon",
        "max_input_channels": 1,
        "default_samplerate": 16000.0,
        "hostapi": 1,
    },
    {
        "name": "Virtual Audio Cable",
        "max_input_channels": 2,
        "default_samplerate": 48000.0,
        "hostapi": 1,
    },
]


@pytest.fixture(autouse=True)
def sahte_sounddevice(monkeypatch: pytest.MonkeyPatch) -> None:
    sd = types.ModuleType("sounddevice")
    sd.query_devices = lambda: AYGITLAR  # type: ignore[attr-defined]
    sd.query_hostapis = lambda: [{"name": "ALSA"}, {"name": "MME"}]  # type: ignore[attr-defined]
    sd.default = types.SimpleNamespace(device=(3, 1))  # varsayılan: sanal kablo  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sounddevice", sd)


def test_only_input_devices_are_listed() -> None:
    adlar = [d.name for d in dev.list_input_devices()]
    assert "Hoparlör" not in adlar
    assert adlar == ["Loopback", "Realtek Mikrofon", "Virtual Audio Cable"]


def test_default_device_is_marked() -> None:
    """Windows'ta varsayılanın sanal kablo olması sessiz kayda yol açmıştı (#12)."""
    varsayilan = [d for d in dev.list_input_devices() if d.is_default]
    assert [d.name for d in varsayilan] == ["Virtual Audio Cable"]


def test_describe_marks_default_with_star() -> None:
    satirlar = [d.describe() for d in dev.list_input_devices()]
    assert any(s.startswith("*") and "Virtual" in s for s in satirlar)
    assert any(s.startswith(" ") and "Realtek" in s for s in satirlar)


def test_none_means_os_default() -> None:
    assert dev.resolve_device(None) is None
    assert dev.resolve_device("") is None


def test_index_is_passed_through() -> None:
    assert dev.resolve_device(2) == 2
    assert dev.resolve_device("2") == 2


def test_unknown_index_lists_available_ones() -> None:
    with pytest.raises(AudioError) as exc:
        dev.resolve_device(99)
    assert "0, 2, 3" in str(exc.value)


def test_name_fragment_is_matched_case_insensitively() -> None:
    assert dev.resolve_device("realtek") == 2


def test_ambiguous_name_is_rejected() -> None:
    """Yanlış aygıttan sessiz kayıt almak, hata vermekten daha kötü."""
    with pytest.raises(AudioError) as exc:
        dev.resolve_device("a")
    assert "birden fazla" in str(exc.value)


def test_unknown_name_points_to_listing_command() -> None:
    with pytest.raises(AudioError) as exc:
        dev.resolve_device("yokbo")
    assert "voxflow devices" in str(exc.value)
