"""ActionDispatcher: yalnızca burada kayıtlı Python fonksiyonları çalışır.

LLM ya da kural motoru hiçbir zaman bir fonksiyon adı/komut üretmez; yalnızca
Intent enum değeri üretir ve bu tabloda karşılığı yoksa işlem yapılmaz.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from voice_assistant.adapters.platforms.launcher import AllowlistLauncher
from voice_assistant.domain.errors import VoxFlowError
from voice_assistant.domain.schemas import (
    ActionResult,
    ActionStatus,
    Intent,
    ValidatedCommand,
)
from voice_assistant.ports.protocols import Store

Handler = Callable[[ValidatedCommand], ActionResult]


def _fmt_date(d: date | None) -> str:
    return d.strftime("%d.%m.%Y") if d else "tarihsiz"


class ActionDispatcher:
    def __init__(self, store: Store, launcher: AllowlistLauncher) -> None:
        self.store = store
        self.launcher = launcher
        self._handlers: dict[Intent, Handler] = {
            Intent.CREATE_NOTE: self._create_note,
            Intent.CREATE_TASK: self._create_task,
            Intent.LIST_TASKS: self._list_tasks,
            Intent.SHOW_HISTORY: self._show_history,
            Intent.CLEAR_HISTORY: self._clear_history,
            Intent.OPEN_APP: self._open_app,
            Intent.OPEN_WEBSITE: self._open_site,
        }

    def execute(self, command: ValidatedCommand) -> ActionResult:
        handler = self._handlers.get(command.intent)
        if handler is None:
            return ActionResult(
                status=ActionStatus.UNSUPPORTED,
                intent=command.intent,
                message=f"'{command.intent}' için kayıtlı bir işlem yok.",
                error_code="E_NO_HANDLER",
            )
        try:
            return handler(command)
        except VoxFlowError as exc:
            return ActionResult(
                status=ActionStatus.ERROR,
                intent=command.intent,
                message=exc.message,
                error_code=exc.code,
            )
        except Exception as exc:  # noqa: BLE001 - beklenmeyen hata da kullanıcıya güvenli dönmeli
            return ActionResult(
                status=ActionStatus.ERROR,
                intent=command.intent,
                message=f"Beklenmeyen hata: {type(exc).__name__}",
                error_code="E_UNEXPECTED",
            )

    # -------------------------------------------------------------- handlers
    def _create_note(self, c: ValidatedCommand) -> ActionResult:
        note = self.store.add_note(str(c.parameters["content"]))
        return ActionResult(
            status=ActionStatus.SUCCESS,
            intent=c.intent,
            message=f"Not kaydedildi: “{note.content}”",
            data={"id": note.id},
        )

    def _create_task(self, c: ValidatedCommand) -> ActionResult:
        due = date.fromisoformat(str(c.parameters["date"])) if c.parameters.get("date") else None
        task = self.store.add_task(str(c.parameters["title"]), due)
        return ActionResult(
            status=ActionStatus.SUCCESS,
            intent=c.intent,
            message=f"Görev eklendi: “{task.title}” ({_fmt_date(task.date)})",
            data={"id": task.id, "date": task.date.isoformat() if task.date else None},
        )

    def _list_tasks(self, c: ValidatedCommand) -> ActionResult:
        due = date.fromisoformat(str(c.parameters["date"])) if c.parameters.get("date") else None
        tasks = self.store.list_tasks(due)
        if not tasks:
            scope = f"{_fmt_date(due)} için " if due else ""
            return ActionResult(
                status=ActionStatus.SUCCESS,
                intent=c.intent,
                message=f"{scope}Kayıtlı görev yok.",
                data={"count": 0},
            )
        lines = [f"  {i}. {t.title} — {_fmt_date(t.date)}" for i, t in enumerate(tasks, 1)]
        return ActionResult(
            status=ActionStatus.SUCCESS,
            intent=c.intent,
            message=f"{len(tasks)} görev:\n" + "\n".join(lines),
            data={"count": len(tasks)},
        )

    def _show_history(self, c: ValidatedCommand) -> ActionResult:
        limit = int(c.parameters.get("limit") or 10)
        entries = self.store.list_history(limit)
        if not entries:
            return ActionResult(
                status=ActionStatus.SUCCESS,
                intent=c.intent,
                message="Geçmiş boş.",
                data={"count": 0},
            )
        lines = [
            f"  [{e.timestamp:%d.%m %H:%M}] “{e.user_text}” → {e.status.value}: "
            f"{e.assistant_message.splitlines()[0]}"
            for e in entries
        ]
        return ActionResult(
            status=ActionStatus.SUCCESS,
            intent=c.intent,
            message=f"Son {len(entries)} kayıt:\n" + "\n".join(lines),
            data={"count": len(entries)},
        )

    def _clear_history(self, c: ValidatedCommand) -> ActionResult:
        if not c.confirmed:
            return ActionResult(
                status=ActionStatus.ERROR,
                intent=c.intent,
                message="Geçmiş silme onaysız çalıştırılamaz.",
                error_code="E_NOT_CONFIRMED",
            )
        n = self.store.clear_history()
        return ActionResult(
            status=ActionStatus.SUCCESS,
            intent=c.intent,
            message=f"Geçmiş temizlendi ({n} kayıt silindi).",
            data={"deleted": n},
        )

    def _open_app(self, c: ValidatedCommand) -> ActionResult:
        exe = self.launcher.open_app(str(c.parameters["app"]))
        return ActionResult(
            status=ActionStatus.SUCCESS,
            intent=c.intent,
            message=f"'{c.parameters['app']}' başlatıldı ({exe}).",
            data={"app": c.parameters["app"]},
        )

    def _open_site(self, c: ValidatedCommand) -> ActionResult:
        url = self.launcher.open_site(str(c.parameters["site"]))
        return ActionResult(
            status=ActionStatus.SUCCESS,
            intent=c.intent,
            message=f"'{c.parameters['site']}' için tarayıcıya açma isteği gönderildi: {url} "
            "(sayfanın yüklenmesi internet bağlantısına bağlıdır).",
            data={"url": url},
        )
