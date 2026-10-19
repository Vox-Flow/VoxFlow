"""Diyalog durumu: bekleyen çok turlu işlem ve bekleyen onay."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from voice_assistant.domain.schemas import Intent


class PendingAction(BaseModel):
    """Eksik parametresi olan, tamamlanmayı bekleyen niyet."""

    model_config = ConfigDict(extra="forbid")

    intent: Intent
    parameters: dict[str, str | int | None] = Field(default_factory=dict)
    missing_parameter: str
    question: str


class PendingConfirmation(BaseModel):
    """Tehlikeli eylem için evet/hayır bekleyen onay."""

    model_config = ConfigDict(extra="forbid")

    intent: Intent
    parameters: dict[str, str | int | None] = Field(default_factory=dict)
    question: str


class DialogueState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pending_action: PendingAction | None = None
    pending_confirmation: PendingConfirmation | None = None
    last_user_text: str | None = None

    @property
    def has_pending(self) -> bool:
        return self.pending_action is not None or self.pending_confirmation is not None

    def clear(self) -> None:
        self.pending_action = None
        self.pending_confirmation = None
