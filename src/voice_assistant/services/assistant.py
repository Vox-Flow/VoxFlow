"""Orkestratör: metin -> niyet -> diyalog kararı -> doğrulanmış komut -> işlem -> geçmiş."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from voice_assistant.domain.dialogue import DialogueState
from voice_assistant.domain.errors import StoreError
from voice_assistant.domain.schemas import ActionResult, ActionStatus, HistoryEntry
from voice_assistant.ports.protocols import ActionExecutor, IntentInterpreter, Store
from voice_assistant.services.dialogue_manager import DialogueManager

log = logging.getLogger("voxflow.assistant")

# Geçmişe yazılmayan ara durumlar (soru/onay turları); geçmiş gerçek sonuçları tutar.
_TRANSIENT = {ActionStatus.NEEDS_CLARIFICATION, ActionStatus.NEEDS_CONFIRMATION}


class Assistant:
    def __init__(
        self,
        interpreter: IntentInterpreter,
        dialogue: DialogueManager,
        executor: ActionExecutor,
        store: Store,
        *,
        record_history: bool = True,
    ) -> None:
        self.interpreter = interpreter
        self.dialogue = dialogue
        self.executor = executor
        self.store = store
        self.state = DialogueState()
        self.record_history = record_history

    def handle_text(self, text: str) -> ActionResult:
        text = text.strip()
        ir = self.interpreter.interpret(text, self.state)
        log.debug("intent=%s params=%s provider=%s", ir.intent, ir.parameters, ir.provider)
        decision = self.dialogue.decide(ir, self.state)
        if decision.result is not None:
            result = decision.result
        else:
            assert decision.command is not None
            result = self.executor.execute(decision.command)
        self.state.last_user_text = text
        self._record(text, result)
        return result

    def _record(self, text: str, result: ActionResult) -> None:
        if not self.record_history or result.status in _TRANSIENT:
            return
        try:
            self.store.append_history(
                HistoryEntry(
                    id=uuid.uuid4().hex[:12],
                    timestamp=datetime.now(),
                    user_text=text,
                    intent=result.intent,
                    status=result.status,
                    assistant_message=result.message,
                    error_code=result.error_code,
                )
            )
        except StoreError as exc:
            log.warning("Geçmiş yazılamadı: %s", exc)
