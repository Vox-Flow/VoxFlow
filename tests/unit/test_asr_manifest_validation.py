"""experiments/asr/validate_manifest.py için smoke test (sentetik manifest)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "asr"))

from validate_manifest import validate  # noqa: E402

ROW = {
    "sample_id": "x1",
    "audio_path": "datasets/audio/spk_01/0001.wav",
    "transcript": "görevleri listele",
    "speaker_id": "spk_01",
    "language": "tr",
    "duration_s": 1.5,
    "split": "train",
    "source": "team",
    "consent_or_license": "team_consent_v1",
    "quality_flags": ["ok"],
}


def _write(tmp_path: Path, rows: list[dict]) -> Path:  # type: ignore[type-arg]
    p = tmp_path / "m.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return p


def test_synthetic_example_manifest_is_valid() -> None:
    rep = validate([ROOT / "datasets/manifests/asr_synthetic_example.jsonl"])
    assert rep.ok, rep.errors
    assert rep.n == 2


def test_speaker_leak_detected(tmp_path: Path) -> None:
    rows = [ROW, {**ROW, "sample_id": "x2", "split": "test"}]
    rep = validate([_write(tmp_path, rows)])
    assert any("sızıntı" in e for e in rep.errors)


def test_missing_consent_is_error(tmp_path: Path) -> None:
    rep = validate([_write(tmp_path, [{**ROW, "consent_or_license": ""}])])
    assert any("consent" in e for e in rep.errors)


def test_duplicate_id_and_bad_split(tmp_path: Path) -> None:
    rep = validate([_write(tmp_path, [ROW, {**ROW, "split": "dev"}])])
    assert any("tekrar eden" in e for e in rep.errors)
    assert any("split" in e for e in rep.errors)


def test_check_files_reports_missing_audio(tmp_path: Path) -> None:
    rep = validate([_write(tmp_path, [ROW])], check_files=True)
    assert any("ses dosyası yok" in e for e in rep.errors)
