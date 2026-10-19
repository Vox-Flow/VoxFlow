import json
from datetime import date

import pytest

from voice_assistant.adapters.storage.json_store import JsonStore
from voice_assistant.domain.errors import StoreCorruptedError


def test_add_and_list_tasks(json_store: JsonStore) -> None:
    json_store.add_task("b", None)
    json_store.add_task("a", date(2026, 10, 20))
    tasks = json_store.list_tasks()
    assert [t.title for t in tasks] == ["a", "b"]  # tarihli önce
    assert [t.title for t in json_store.list_tasks(date(2026, 10, 20))] == ["a"]
    raw = json.loads((json_store.data_dir / "tasks.json").read_text(encoding="utf-8"))
    assert raw["version"] == 1 and len(raw["items"]) == 2


def test_notes_roundtrip(json_store: JsonStore) -> None:
    n = json_store.add_note("süt al")
    assert json_store.list_notes()[0].content == "süt al"
    assert n.id


def test_history_clear_returns_count(json_store: JsonStore) -> None:
    from datetime import datetime

    from voice_assistant.domain.schemas import ActionStatus, HistoryEntry, Intent

    for i in range(3):
        json_store.append_history(
            HistoryEntry(
                id=str(i),
                timestamp=datetime.now(),
                user_text="x",
                intent=Intent.LIST_TASKS,
                status=ActionStatus.SUCCESS,
                assistant_message="ok",
            )
        )
    assert len(json_store.list_history()) == 3
    assert len(json_store.list_history(limit=2)) == 2
    assert json_store.clear_history() == 3
    assert json_store.list_history() == []


def test_corrupted_file_raises(json_store: JsonStore) -> None:
    (json_store.data_dir / "tasks.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(StoreCorruptedError):
        json_store.list_tasks()


def test_wrong_shape_raises(json_store: JsonStore) -> None:
    (json_store.data_dir / "notes.json").write_text(
        '{"version": 1, "items": "x"}', encoding="utf-8"
    )
    with pytest.raises(StoreCorruptedError):
        json_store.list_notes()


def test_backup_created_on_rewrite(json_store: JsonStore) -> None:
    json_store.add_task("a", None)
    json_store.add_task("b", None)
    assert (json_store.data_dir / "tasks.json.bak").exists()


def test_no_temp_files_left(json_store: JsonStore) -> None:
    json_store.add_note("x")
    assert not list(json_store.data_dir.glob(".*.tmp"))


def test_store_has_no_delete_for_tasks_or_notes() -> None:
    assert not any(
        n.startswith(("delete", "remove", "update", "edit", "complete")) for n in dir(JsonStore)
    )
