"""Tutulmuş NLU test kümesinin (nlu_test_v2) bütünlüğü.

Bu küme **dondurulmuştur**: yalnızca son ölçümde kullanılır. Test, kümenin şemaya
uygunluğunu ve geliştirme kümesiyle örtüşmediğini korur — örtüşme olursa ölçüm
bağımsızlığını kaybeder.
"""

import json
from pathlib import Path

from voice_assistant.domain.schemas import Intent

ROOT = Path(__file__).resolve().parents[2]
HOLDOUT = ROOT / "datasets" / "manifests" / "nlu_test_v2.jsonl"
DEV = ROOT / "datasets" / "manifests" / "nlu_dev_v1.jsonl"

FIELDS = {"sample_id", "utterance", "intent", "slots", "dialogue_context", "split", "source"}


def _rows(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_holdout_rows_match_schema() -> None:
    rows = _rows(HOLDOUT)
    assert len(rows) >= 30, "küme en az 30 örnek olmalı (#35)"
    for row in rows:
        assert set(row) == FIELDS, row["sample_id"]
        assert row["intent"] in set(Intent), row["sample_id"]
        assert row["split"] == "test"
        assert row["source"] == "team_written_holdout"


def test_sample_ids_are_unique() -> None:
    ids = [row["sample_id"] for row in _rows(HOLDOUT)]
    assert len(ids) == len(set(ids))


def test_holdout_does_not_overlap_dev_set() -> None:
    """Aynı cümle iki kümede olursa tutulmuş küme bağımsız olmaktan çıkar."""
    holdout = {row["utterance"].strip().lower() for row in _rows(HOLDOUT)}
    dev = {row["utterance"].strip().lower() for row in _rows(DEV)}
    assert not (holdout & dev)


def test_every_action_intent_is_represented() -> None:
    """Rapordaki makro-F1 anlamlı olsun diye her niyetten en az bir örnek."""
    seen = {row["intent"] for row in _rows(HOLDOUT)}
    missing = {intent.value for intent in Intent} - seen
    assert not missing, f"kümede temsil edilmeyen niyet: {sorted(missing)}"
