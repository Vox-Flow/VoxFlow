"""Faz 1 kabul testleri: uçtan uca metin akışları (ses/LLM yok)."""

from voice_assistant.domain.schemas import ActionStatus, Intent


def test_task_with_clarification_saves(assistant, store) -> None:  # type: ignore[no-untyped-def]
    r1 = assistant.handle_text("görev ekle")
    assert r1.status == ActionStatus.NEEDS_CLARIFICATION
    assert "ad" in r1.message.lower()
    assert store.list_tasks() == []
    r2 = assistant.handle_text("Matematik ödevi")
    assert r2.status == ActionStatus.SUCCESS, r2
    tasks = store.list_tasks()
    assert len(tasks) == 1 and tasks[0].title == "Matematik ödevi" and tasks[0].date is None
    assert assistant.state.pending_action is None


def test_task_then_cancel_saves_nothing(assistant, store) -> None:  # type: ignore[no-untyped-def]
    assert assistant.handle_text("görev ekle").status == ActionStatus.NEEDS_CLARIFICATION
    r = assistant.handle_text("vazgeçtim")
    assert r.status == ActionStatus.CANCELLED
    assert store.list_tasks() == []
    assert not assistant.state.has_pending
    # geçmişte iptal kaydı var, ara soru yok
    hist = store.list_history()
    assert [h.status for h in hist] == [ActionStatus.CANCELLED]


def test_cancel_without_pending(assistant) -> None:  # type: ignore[no-untyped-def]
    r = assistant.handle_text("iptal et")
    assert r.status == ActionStatus.CANCELLED and "yok" in r.message


def test_task_one_shot_with_date(assistant, store) -> None:  # type: ignore[no-untyped-def]
    r = assistant.handle_text("yarın için matematik ödevi görevi ekle")
    assert r.status == ActionStatus.SUCCESS
    t = store.list_tasks()[0]
    assert t.title == "matematik ödevi" and t.date.isoformat() == "2026-10-20"
    r2 = assistant.handle_text("görevleri listele")
    assert (
        r2.status == ActionStatus.SUCCESS
        and "matematik ödevi" in r2.message
        and "20.10.2026" in r2.message
    )


def test_note_flow(assistant, store) -> None:  # type: ignore[no-untyped-def]
    assert assistant.handle_text("not al").status == ActionStatus.NEEDS_CLARIFICATION
    r = assistant.handle_text("yarın süt al")
    assert r.status == ActionStatus.SUCCESS
    assert store.list_notes()[0].content == "yarın süt al"


def test_clear_history_requires_confirmation(assistant, store) -> None:  # type: ignore[no-untyped-def]
    assistant.handle_text("görevleri listele")
    assert len(store.list_history()) == 1
    r = assistant.handle_text("geçmişi sil")
    assert r.status == ActionStatus.NEEDS_CONFIRMATION
    assert len(store.list_history()) == 1  # henüz silinmedi
    r2 = assistant.handle_text("hayır")
    assert r2.status == ActionStatus.CANCELLED
    assert len(store.list_history()) == 2  # listele + vazgeçme kaydı; silinmedi
    assistant.handle_text("geçmişi sil")
    r3 = assistant.handle_text("evet")
    assert r3.status == ActionStatus.SUCCESS and r3.data["deleted"] == 2
    # silme sonrası yalnızca silme işleminin kendi kaydı kalır
    assert [h.intent for h in store.list_history()] == [Intent.CLEAR_HISTORY]


def test_clear_history_cancel_word_also_aborts(assistant, store) -> None:  # type: ignore[no-untyped-def]
    assistant.handle_text("geçmişi sil")
    r = assistant.handle_text("vazgeçtim")
    assert r.status == ActionStatus.CANCELLED
    assert assistant.state.pending_confirmation is None


def test_open_app_and_site(assistant, launcher) -> None:  # type: ignore[no-untyped-def]
    r = assistant.handle_text("firefox aç")
    assert r.status == ActionStatus.SUCCESS and launcher.spawned == [("firefox",)]
    r2 = assistant.handle_text("youtube'u aç")
    assert r2.status == ActionStatus.SUCCESS and launcher.opened == ["https://www.youtube.com"]
    assert "isteği gönderildi" in r2.message and "yüklendi" not in r2.message


def test_open_unknown_app_does_nothing(assistant, launcher) -> None:  # type: ignore[no-untyped-def]
    r = assistant.handle_text("photoshop aç")
    assert r.status == ActionStatus.NEEDS_CLARIFICATION
    assert launcher.spawned == [] and launcher.opened == []
    r2 = assistant.handle_text("firefox")
    assert r2.status == ActionStatus.SUCCESS and launcher.spawned == [("firefox",)]


def test_unsupported_lists_alternatives(assistant, store) -> None:  # type: ignore[no-untyped-def]
    r = assistant.handle_text("matematik görevini sil")
    assert r.status == ActionStatus.UNSUPPORTED
    assert "desteklenmiyor" in r.message and "görev ekle" in r.message
    assert store.list_tasks() == []


def test_unknown_keeps_pending_and_repeats_question(assistant) -> None:  # type: ignore[no-untyped-def]
    assistant.handle_text("görev ekle")
    # bekleyen başlık varken herhangi bir metin başlık olur; bu beklenen davranış.
    r = assistant.handle_text("fizik")
    assert r.status == ActionStatus.SUCCESS


def test_show_history(assistant) -> None:  # type: ignore[no-untyped-def]
    assistant.handle_text("not al deneme")
    r = assistant.handle_text("geçmişi göster")
    assert r.status == ActionStatus.SUCCESS and "deneme" in r.message


def test_app_missing_binary_is_error(interpreter, store) -> None:  # type: ignore[no-untyped-def]
    from tests.conftest import SpyLauncher, make_assistant

    launcher = SpyLauncher(which_ok=False)
    a = make_assistant(interpreter, store, launcher)
    r = a.handle_text("firefox aç")
    assert r.status == ActionStatus.ERROR and r.error_code == "E_APP_NOT_FOUND"
    assert store.list_history()[0].error_code == "E_APP_NOT_FOUND"
