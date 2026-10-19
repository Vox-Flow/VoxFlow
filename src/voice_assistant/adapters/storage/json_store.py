"""JSON tabanlı yerel depo: not/görev/geçmiş.

Güvenlik/bütünlük: atomik yazım (tmp + os.replace), sürüm alanı, bozuk dosya
hatası (E_STORE_CORRUPTED), her yazımdan önce `.bak` yedeği. Kapsam bilerek dar:
not/görev için yalnızca ekle/listele; silme yalnızca geçmiş için vardır.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from voice_assistant.domain.errors import StoreCorruptedError, StoreError
from voice_assistant.domain.schemas import HistoryEntry, Note, Task

SCHEMA_VERSION = 1


def default_data_dir(app_name: str = "voxflow") -> Path:
    """Platforma uygun kullanıcı veri dizini (ek bağımlılık olmadan)."""
    env = os.environ.get("VOXFLOW_DATA_DIR")
    if env:
        return Path(env).expanduser()
    home = Path.home()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        return base / app_name
    if os.uname().sysname == "Darwin":  # pragma: no cover - macOS yolunda test edilmedi
        return home / "Library" / "Application Support" / app_name
    xdg = os.environ.get("XDG_DATA_HOME")
    return (Path(xdg) if xdg else home / ".local" / "share") / app_name


class JsonStore:
    def __init__(self, data_dir: Path, *, keep_backup: bool = True) -> None:
        self.data_dir = Path(data_dir)
        self.keep_backup = keep_backup
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StoreError(f"Veri dizini oluşturulamadı: {self.data_dir} ({exc})") from exc
        self._paths = {
            "notes": self.data_dir / "notes.json",
            "tasks": self.data_dir / "tasks.json",
            "history": self.data_dir / "history.json",
        }

    # ------------------------------------------------------------ low level io
    def _read(self, kind: str) -> list[dict[str, Any]]:
        path = self._paths[kind]
        if not path.exists():
            return []
        try:
            raw = path.read_text(encoding="utf-8")
            doc = json.loads(raw) if raw.strip() else {"version": SCHEMA_VERSION, "items": []}
        except (OSError, json.JSONDecodeError) as exc:
            raise StoreCorruptedError(
                f"{path.name} okunamadı veya bozuk. Yedek: {path.with_suffix('.json.bak')}"
            ) from exc
        if not isinstance(doc, dict) or "items" not in doc or not isinstance(doc["items"], list):
            raise StoreCorruptedError(f"{path.name} beklenen yapıda değil (items listesi yok).")
        if doc.get("version") != SCHEMA_VERSION:
            raise StoreCorruptedError(
                f"{path.name} şema sürümü {doc.get('version')!r}; beklenen {SCHEMA_VERSION}."
            )
        return [i for i in doc["items"] if isinstance(i, dict)]

    def _write(self, kind: str, items: list[dict[str, Any]]) -> None:
        path = self._paths[kind]
        if self.keep_backup and path.exists():
            try:
                shutil.copy2(path, path.with_suffix(".json.bak"))
            except OSError:
                pass  # yedek alınamaması yazımı engellemez
        payload = json.dumps(
            {"version": SCHEMA_VERSION, "items": items}, ensure_ascii=False, indent=2
        )
        fd, tmp_name = tempfile.mkstemp(dir=self.data_dir, prefix=f".{kind}-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, path)
        except OSError as exc:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise StoreError(f"{path.name} yazılamadı: {exc}") from exc

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:12]

    # ----------------------------------------------------------------- notes
    def add_note(self, content: str) -> Note:
        note = Note(id=self._new_id(), content=content.strip(), created_at=datetime.now())
        items = self._read("notes")
        items.append(note.model_dump(mode="json"))
        self._write("notes", items)
        return note

    def list_notes(self) -> list[Note]:
        return [self._parse(Note, i, "notes") for i in self._read("notes")]

    # ----------------------------------------------------------------- tasks
    def add_task(self, title: str, due: date | None) -> Task:
        task = Task(id=self._new_id(), title=title.strip(), date=due, created_at=datetime.now())
        items = self._read("tasks")
        items.append(task.model_dump(mode="json"))
        self._write("tasks", items)
        return task

    def list_tasks(self, due: date | None = None) -> list[Task]:
        tasks = [self._parse(Task, i, "tasks") for i in self._read("tasks")]
        if due is not None:
            tasks = [t for t in tasks if t.date == due]
        return sorted(tasks, key=lambda t: (t.date is None, t.date or date.max, t.created_at))

    # --------------------------------------------------------------- history
    def append_history(self, entry: HistoryEntry) -> None:
        items = self._read("history")
        items.append(entry.model_dump(mode="json"))
        self._write("history", items)

    def list_history(self, limit: int | None = None) -> list[HistoryEntry]:
        entries = [self._parse(HistoryEntry, i, "history") for i in self._read("history")]
        entries.sort(key=lambda e: e.timestamp)
        return entries[-limit:] if limit else entries

    def clear_history(self) -> int:
        count = len(self._read("history"))
        self._write("history", [])
        return count

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _parse(model: type, item: dict[str, Any], kind: str) -> Any:
        try:
            return model.model_validate(item)
        except PydanticValidationError as exc:
            raise StoreCorruptedError(
                f"{kind}.json içinde geçersiz kayıt: {exc.errors()[0]['msg']}"
            ) from exc


class InMemoryStore(JsonStore):
    """Testler için diske dokunmayan depo (aynı sözleşme)."""

    def __init__(self) -> None:  # noqa: D107
        self._mem: dict[str, list[dict[str, Any]]] = {"notes": [], "tasks": [], "history": []}
        self.data_dir = Path(":memory:")
        self.keep_backup = False

    def _read(self, kind: str) -> list[dict[str, Any]]:
        return [dict(i) for i in self._mem[kind]]

    def _write(self, kind: str, items: list[dict[str, Any]]) -> None:
        self._mem[kind] = [dict(i) for i in items]
