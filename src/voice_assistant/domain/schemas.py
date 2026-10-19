"""Modelden bağımsız veri sözleşmeleri.

Bu dosyadaki modeller ASR, NLU (kurallı / LLM / fine-tuned) ve test (mock)
adaptörlerinin ortak dili olup, LLM'in ürettiği her şey burada doğrulanır.
Doğrulamadan geçmeyen hiçbir alan işlem başlatamaz.
"""

from __future__ import annotations

import datetime as _dt
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Intent(StrEnum):
    """İlk sürüm niyet kataloğu.

    Eylem niyetleri: open_app, open_website, create_note, create_task,
    list_tasks, show_history, clear_history.
    Diyalog niyetleri (eylem değil): cancel, affirm, deny.
    Ret niyetleri: unknown (anlaşılamadı), unsupported (anlaşıldı ama izinli değil).
    """

    OPEN_APP = "open_app"
    OPEN_WEBSITE = "open_website"
    CREATE_NOTE = "create_note"
    CREATE_TASK = "create_task"
    LIST_TASKS = "list_tasks"
    SHOW_HISTORY = "show_history"
    CLEAR_HISTORY = "clear_history"
    CANCEL = "cancel"
    AFFIRM = "affirm"
    DENY = "deny"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"


ACTION_INTENTS: frozenset[Intent] = frozenset(
    {
        Intent.OPEN_APP,
        Intent.OPEN_WEBSITE,
        Intent.CREATE_NOTE,
        Intent.CREATE_TASK,
        Intent.LIST_TASKS,
        Intent.SHOW_HISTORY,
        Intent.CLEAR_HISTORY,
    }
)

# Her eylem niyeti için izin verilen parametre adları ve zorunlu olanlar.
# Buradaki listede olmayan anahtarlar doğrulayıcı tarafından atılır.
ALLOWED_PARAMETERS: dict[Intent, frozenset[str]] = {
    Intent.OPEN_APP: frozenset({"app"}),
    Intent.OPEN_WEBSITE: frozenset({"site"}),
    Intent.CREATE_NOTE: frozenset({"content"}),
    Intent.CREATE_TASK: frozenset({"title", "date"}),
    Intent.LIST_TASKS: frozenset({"date"}),
    Intent.SHOW_HISTORY: frozenset({"limit"}),
    Intent.CLEAR_HISTORY: frozenset(),
}
REQUIRED_PARAMETERS: dict[Intent, frozenset[str]] = {
    Intent.OPEN_APP: frozenset({"app"}),
    Intent.OPEN_WEBSITE: frozenset({"site"}),
    Intent.CREATE_NOTE: frozenset({"content"}),
    Intent.CREATE_TASK: frozenset({"title"}),
    Intent.LIST_TASKS: frozenset(),
    Intent.SHOW_HISTORY: frozenset(),
    Intent.CLEAR_HISTORY: frozenset(),
}
# Doğrulayıcının onay istediği tehlikeli niyetler.
CONFIRMATION_REQUIRED: frozenset[Intent] = frozenset({Intent.CLEAR_HISTORY})


class Transcript(BaseModel):
    """SpeechRecognizer çıktısı."""

    model_config = ConfigDict(extra="forbid")

    text: str
    language: str = "tr"
    duration_s: float | None = None
    latency_s: float | None = None
    provider: str = "unknown"
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class IntentResult(BaseModel):
    """IntentInterpreter çıktısı. Hem kurallı hem LLM adaptörleri bunu üretir.

    `extra="ignore"` ile modelin ürettiği bilinmeyen anahtarlar sessizce atılır;
    parametreler ayrıca CommandValidator'da allowlist'e göre süzülür.
    """

    model_config = ConfigDict(extra="ignore")

    intent: Intent
    parameters: dict[str, Any] = Field(default_factory=dict)
    needs_clarification: bool = False
    clarification_question: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    provider: str = "unknown"
    raw_text: str = ""

    @field_validator("parameters")
    @classmethod
    def _only_scalar_params(cls, v: dict[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for k, val in v.items():
            if not isinstance(k, str):
                continue
            if val is None or isinstance(val, str | int | float | bool):
                cleaned[k] = val
        return cleaned


class ValidatedCommand(BaseModel):
    """CommandValidator'dan geçmiş, dispatcher'ın çalıştırmaya hak kazandığı komut."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    intent: Intent
    parameters: dict[str, str | int | None]
    confirmed: bool = False


class ActionStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    CANCELLED = "cancelled"
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_CONFIRMATION = "needs_confirmation"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class ActionResult(BaseModel):
    """Gerçek işlem sonucu. `message` kullanıcıya Türkçe gösterilir."""

    model_config = ConfigDict(extra="forbid")

    status: ActionStatus
    message: str
    intent: Intent | None = None
    error_code: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == ActionStatus.SUCCESS


class Note(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    content: str = Field(min_length=1, max_length=2000)
    created_at: datetime


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str = Field(min_length=1, max_length=300)
    date: _dt.date | None = None  # alan adı tipi gölgelediği için modül takma adı
    created_at: datetime


class HistoryEntry(BaseModel):
    """Kalıcı geçmiş kaydı. Ham ses saklanmaz; yalnızca metin ve sonuç."""

    model_config = ConfigDict(extra="forbid")

    id: str
    timestamp: datetime
    user_text: str
    intent: Intent | None
    status: ActionStatus
    assistant_message: str
    error_code: str | None = None
