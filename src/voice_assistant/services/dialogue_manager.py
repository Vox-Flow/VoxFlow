"""DialogueManager: bekleyen işlem, eksik parametre, onay ve iptal akışı.

Karar tablosu:
- cancel: bekleyen bir şey varsa iptal eder; yoksa "iptal edilecek işlem yok".
- affirm/deny: yalnızca bekleyen onay varsa anlamlı.
- eylem niyeti: validator'dan geçer -> ya çalıştır, ya soru sor, ya onay iste.
- unknown/unsupported: bekleyen işlem korunur, kullanıcıya bilgi verilir.
"""

from __future__ import annotations

from dataclasses import dataclass

from voice_assistant.domain.dialogue import DialogueState, PendingAction, PendingConfirmation
from voice_assistant.domain.schemas import (
    ACTION_INTENTS,
    ActionResult,
    ActionStatus,
    Intent,
    IntentResult,
    ValidatedCommand,
)
from voice_assistant.services.validator import CommandValidator

UNSUPPORTED_HINT = (
    "Yapabildiklerim: görev ekle, not al, görevleri listele, geçmişi göster/sil, "
    "izinli uygulama veya siteyi aç."
)


@dataclass(frozen=True)
class Decision:
    """Ya çalıştırılacak komut ya da doğrudan kullanıcıya dönecek sonuç."""

    command: ValidatedCommand | None = None
    result: ActionResult | None = None


class DialogueManager:
    def __init__(self, validator: CommandValidator) -> None:
        self.validator = validator

    def decide(self, ir: IntentResult, state: DialogueState) -> Decision:
        intent = ir.intent

        if intent == Intent.CANCEL:
            if state.has_pending:
                what = (
                    state.pending_action.intent
                    if state.pending_action
                    else state.pending_confirmation.intent  # type: ignore[union-attr]
                )
                state.clear()
                return Decision(
                    result=ActionResult(
                        status=ActionStatus.CANCELLED,
                        intent=Intent.CANCEL,
                        message=f"İptal edildi ({what}). Hiçbir şey kaydedilmedi.",
                    )
                )
            return Decision(
                result=ActionResult(
                    status=ActionStatus.CANCELLED,
                    intent=Intent.CANCEL,
                    message="İptal edilecek bekleyen bir işlem yok.",
                )
            )

        if intent in (Intent.AFFIRM, Intent.DENY):
            pc = state.pending_confirmation
            if pc is None:
                return Decision(
                    result=ActionResult(
                        status=ActionStatus.UNKNOWN,
                        intent=Intent.UNKNOWN,
                        message="Onaylanacak bekleyen bir işlem yok. " + UNSUPPORTED_HINT,
                    )
                )
            state.clear()
            if intent == Intent.DENY:
                return Decision(
                    result=ActionResult(
                        status=ActionStatus.CANCELLED,
                        intent=pc.intent,
                        message=f"Vazgeçildi ({pc.intent}). Hiçbir şey silinmedi.",
                    )
                )
            return Decision(
                command=ValidatedCommand(intent=pc.intent, parameters=pc.parameters, confirmed=True)
            )

        if intent == Intent.UNSUPPORTED:
            req = ir.parameters.get("requested")
            msg = f"'{req}' ilk sürümde desteklenmiyor. " if req else "Bu istek desteklenmiyor. "
            return Decision(
                result=ActionResult(
                    status=ActionStatus.UNSUPPORTED,
                    intent=Intent.UNSUPPORTED,
                    message=msg + UNSUPPORTED_HINT,
                    error_code="E_UNSUPPORTED",
                )
            )

        if intent == Intent.UNKNOWN:
            msg = ir.clarification_question or ("Bunu anlayamadım. " + UNSUPPORTED_HINT)
            if state.pending_action:
                msg = f"{state.pending_action.question} (İptal için 'vazgeçtim' diyebilirsiniz.)"
            elif state.pending_confirmation:
                msg = f"{state.pending_confirmation.question} (evet / hayır)"
            return Decision(
                result=ActionResult(status=ActionStatus.UNKNOWN, intent=Intent.UNKNOWN, message=msg)
            )

        if intent not in ACTION_INTENTS:  # savunma amaçlı
            return Decision(
                result=ActionResult(
                    status=ActionStatus.UNSUPPORTED,
                    intent=intent,
                    message="Bu niyet için işlem tanımlı değil.",
                    error_code="E_UNSUPPORTED",
                )
            )

        # Yeni eylem niyeti: önceki bekleyen işlem (varsa) iptal sayılır.
        if state.pending_action and state.pending_action.intent != intent:
            state.pending_action = None
        state.pending_confirmation = None

        outcome = self.validator.validate(ir)
        if outcome.error:
            return Decision(
                result=ActionResult(
                    status=ActionStatus.ERROR,
                    intent=intent,
                    message=outcome.error,
                    error_code="E_VALIDATION",
                )
            )
        if outcome.missing_parameter:
            kept = {k: v for k, v in ir.parameters.items() if k in ("date",)}
            state.pending_action = PendingAction(
                intent=intent,
                parameters={
                    k: (v if isinstance(v, str | int) or v is None else str(v))
                    for k, v in kept.items()
                },
                missing_parameter=outcome.missing_parameter,
                question=outcome.question or "Eksik bilgiyi belirtir misiniz?",
            )
            return Decision(
                result=ActionResult(
                    status=ActionStatus.NEEDS_CLARIFICATION,
                    intent=intent,
                    message=state.pending_action.question,
                )
            )
        assert outcome.command is not None
        if outcome.needs_confirmation:
            q = "Tüm konuşma geçmişi kalıcı olarak silinecek. Onaylıyor musunuz? (evet / hayır)"
            state.pending_confirmation = PendingConfirmation(
                intent=intent, parameters=dict(outcome.command.parameters), question=q
            )
            return Decision(
                result=ActionResult(
                    status=ActionStatus.NEEDS_CONFIRMATION, intent=intent, message=q
                )
            )
        state.clear()
        return Decision(command=outcome.command)
