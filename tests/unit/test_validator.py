from voice_assistant.domain.schemas import Intent, IntentResult
from voice_assistant.services.validator import CommandValidator


def v() -> CommandValidator:
    return CommandValidator({"firefox"}, {"youtube"})


def test_unknown_keys_are_dropped() -> None:
    ir = IntentResult(
        intent=Intent.CREATE_TASK, parameters={"title": "x", "shell": "rm -rf /", "path": "/etc"}
    )
    out = v().validate(ir)
    assert out.ok
    assert set(out.command.parameters) == {"title"}


def test_missing_required_asks_question() -> None:
    out = v().validate(IntentResult(intent=Intent.CREATE_TASK, parameters={"date": "2026-10-20"}))
    assert not out.ok
    assert out.missing_parameter == "title"
    assert out.question


def test_bad_date_is_error_not_guess() -> None:
    out = v().validate(
        IntentResult(intent=Intent.CREATE_TASK, parameters={"title": "x", "date": "yarın"})
    )
    assert out.error and "Tarih" in out.error


def test_app_not_in_allowlist() -> None:
    out = v().validate(IntentResult(intent=Intent.OPEN_APP, parameters={"app": "photoshop"}))
    assert out.error and "izin" in out.error


def test_site_not_in_allowlist() -> None:
    out = v().validate(
        IntentResult(intent=Intent.OPEN_WEBSITE, parameters={"site": "http://evil.example"})
    )
    assert out.error


def test_clear_history_needs_confirmation() -> None:
    out = v().validate(IntentResult(intent=Intent.CLEAR_HISTORY))
    assert out.needs_confirmation and out.command is not None and not out.command.confirmed
    out2 = v().validate(IntentResult(intent=Intent.CLEAR_HISTORY), confirmed=True)
    assert not out2.needs_confirmation and out2.command.confirmed


def test_non_action_intent_rejected() -> None:
    assert v().validate(IntentResult(intent=Intent.CANCEL)).error


def test_title_too_long() -> None:
    out = v().validate(IntentResult(intent=Intent.CREATE_TASK, parameters={"title": "a" * 301}))
    assert out.error


def test_intent_result_ignores_nested_params() -> None:
    ir = IntentResult(
        intent=Intent.CREATE_NOTE, parameters={"content": "x", "cmd": ["rm", "-rf"]}, extra_key=1
    )  # type: ignore[call-arg]
    assert "cmd" not in ir.parameters
