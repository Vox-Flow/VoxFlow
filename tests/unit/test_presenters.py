"""Sunum adaptörleri: düz metin sözleşmesi, rich adaptörü, seçim mantığı."""

import io

import pytest

from voice_assistant.adapters.ui import build_presenter
from voice_assistant.adapters.ui.console import ConsolePresenter
from voice_assistant.domain.schemas import ActionResult, ActionStatus, Intent
from voice_assistant.ports.protocols import ResponsePresenter


class FakeTts:
    """speak() sonucu ve adı parametreli sahte TTS."""

    def __init__(self, name: str = "pyttsx3", *, available: bool = True, speaks: bool = True):
        self._name = name
        self._available = available
        self._speaks = speaks
        self.spoken: list[str] = []

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return self._available

    def speak(self, text: str) -> bool:
        self.spoken.append(text)
        return self._speaks


def ok_result(message: str = "Görev eklendi.") -> ActionResult:
    return ActionResult(status=ActionStatus.SUCCESS, intent=Intent.CREATE_TASK, message=message)


def err_result() -> ActionResult:
    return ActionResult(
        status=ActionStatus.ERROR, message="Uygulama açılamadı.", error_code="E_LAUNCH"
    )


# --- düz metin: mevcut çıktı sözleşmesi korunmalı -------------------------------


def test_console_status_and_show_format() -> None:
    out = io.StringIO()
    p = ConsolePresenter(out=out)
    p.status("komut doğrulanıyor")
    p.show(ok_result())
    assert out.getvalue() == "[komut doğrulanıyor]\n[✔ başarılı] Görev eklendi.\n"


def test_console_shows_error_code() -> None:
    out = io.StringIO()
    ConsolePresenter(out=out).show(err_result())
    assert out.getvalue() == "[✖ hata (E_LAUNCH)] Uygulama açılamadı.\n"


def test_console_speaks_first_line_only() -> None:
    tts = FakeTts()
    out = io.StringIO()
    ConsolePresenter(tts, out).show(ok_result("2 görev:\n  1. Ödev — bugün"))
    assert tts.spoken == ["2 görev:"]
    assert "tts:" not in out.getvalue()


def test_console_notes_failed_tts() -> None:
    out = io.StringIO()
    ConsolePresenter(FakeTts(speaks=False), out).show(ok_result())
    assert "ses üretilemedi" in out.getvalue()


def test_console_silent_fallback_needs_no_note() -> None:
    """Konsol TTS'i zaten sessizdir; her mesajda uyarı basılmamalı."""
    out = io.StringIO()
    ConsolePresenter(FakeTts("console", speaks=False), out).show(ok_result())
    assert "ses üretilemedi" not in out.getvalue()


def test_console_satisfies_port() -> None:
    assert isinstance(ConsolePresenter(), ResponsePresenter)


# --- rich adaptörü --------------------------------------------------------------


def test_rich_presenter_renders_message_and_label() -> None:
    pytest.importorskip("rich")
    from voice_assistant.adapters.ui.rich_ui import RichPresenter

    out = io.StringIO()
    p = RichPresenter(out=out, width=60)
    assert isinstance(p, ResponsePresenter)
    p.status("ses çözümleniyor")
    p.show(err_result())
    text = out.getvalue()
    assert "[ses çözümleniyor]" in text
    assert "Uygulama açılamadı." in text and "E_LAUNCH" in text


def test_rich_presenter_does_not_eat_brackets_as_markup() -> None:
    """Geçmiş satırları [12.03 09:40] gibi köşeli parantez içerir; kaybolmamalı."""
    pytest.importorskip("rich")
    from voice_assistant.adapters.ui.rich_ui import RichPresenter

    out = io.StringIO()
    RichPresenter(out=out, width=70).show(ok_result("[12.03 09:40] “not al” → success"))
    assert "[12.03 09:40]" in out.getvalue()


def test_rich_presenter_speaks_too() -> None:
    pytest.importorskip("rich")
    from voice_assistant.adapters.ui.rich_ui import RichPresenter

    tts = FakeTts()
    RichPresenter(tts, io.StringIO(), width=60).show(ok_result())
    assert tts.spoken == ["Görev eklendi."]


# --- seçim mantığı --------------------------------------------------------------


class _FakeTty(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_plain_is_forced_even_on_tty() -> None:
    assert build_presenter("plain", out=_FakeTty()).name == "plain"


def test_auto_uses_plain_when_not_a_tty() -> None:
    """Boruya/dosyaya yazarken ANSI kaçış kodu üretilmemeli."""
    assert build_presenter("auto", out=io.StringIO()).name == "plain"


def test_auto_uses_rich_on_tty_when_installed() -> None:
    pytest.importorskip("rich")
    assert build_presenter("auto", out=_FakeTty()).name == "rich"


def test_rich_request_falls_back_with_warning_when_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """rich kurulu değilse çökme yok; düz metne düşülür ve kullanıcı bilgilendirilir."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name.startswith("rich"):
            raise ImportError("rich yok")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(
        __import__("sys").modules, "voice_assistant.adapters.ui.rich_ui", raising=False
    )
    monkeypatch.setattr(builtins, "__import__", fake_import)
    warnings: list[str] = []
    p = build_presenter("rich", out=_FakeTty(), warnings=warnings)
    assert p.name == "plain"
    assert warnings and "rich kurulu değil" in warnings[0]


def test_auto_fallback_is_silent_when_rich_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """auto modunda rich yokluğu normal durumdur; uyarı gürültüsü yapılmaz."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name.startswith("rich"):
            raise ImportError("rich yok")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(
        __import__("sys").modules, "voice_assistant.adapters.ui.rich_ui", raising=False
    )
    monkeypatch.setattr(builtins, "__import__", fake_import)
    warnings: list[str] = []
    assert build_presenter("auto", out=_FakeTty(), warnings=warnings).name == "plain"
    assert warnings == []
