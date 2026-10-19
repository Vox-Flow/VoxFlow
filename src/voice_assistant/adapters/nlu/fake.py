"""Test için önceden tanımlı yanıtlar döndüren IntentInterpreter."""

from __future__ import annotations

from voice_assistant.domain.dialogue import DialogueState
from voice_assistant.domain.schemas import Intent, IntentResult


class FakeInterpreter:
    def __init__(self, mapping: dict[str, IntentResult] | None = None) -> None:
        self.mapping = mapping or {}
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return "fake"

    def interpret(self, text: str, state: DialogueState) -> IntentResult:
        self.calls.append(text)
        return self.mapping.get(
            text, IntentResult(intent=Intent.UNKNOWN, provider=self.name, raw_text=text)
        )
