"""Kayıt oturumu mantığı: mikrofon, numpy veya soundfile gerektirmez."""

import csv
import json
import math
import sys
from pathlib import Path

import pytest

from voice_assistant.domain.errors import StoreError, ValidationError
from voice_assistant.services.recording import (
    RecordingSession,
    Sentence,
    drop_sample,
    load_sentences,
    mark_verified,
    quality_flags,
    read_wav_pcm16,
    update_transcript,
    write_wav_pcm16,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FIELDS = {
    "sample_id",
    "audio_path",
    "transcript",
    "speaker_id",
    "language",
    "duration_s",
    "split",
    "source",
    "consent_or_license",
    "quality_flags",
}


def tone(seconds: float = 1.0, amplitude: float = 0.3, rate: int = 16000) -> list[float]:
    return [amplitude * math.sin(2 * math.pi * 440 * i / rate) for i in range(int(seconds * rate))]


def make_session(tmp_path: Path, **kw) -> RecordingSession:  # type: ignore[no-untyped-def]
    defaults = dict(
        speaker_id="spk_01",
        session_id="s01",
        split="train",
        consent="team_consent_v1",
        audio_root=tmp_path / "audio",
        manifest_path=tmp_path / "manifests" / "asr_spk_01_real.jsonl",
    )
    defaults.update(kw)
    return RecordingSession(**defaults)  # type: ignore[arg-type]


# --------------------------------------------------------------- cümle listesi
def test_load_project_sentence_list_has_100_unique() -> None:
    sentences = load_sentences(ROOT / "docs/recording_sentences_tr.md")
    assert len(sentences) == 100
    assert len({s.id for s in sentences}) == 100
    assert sentences[0].id == "C001" and "matematik" in sentences[0].text.lower()


def test_load_sentences_rejects_duplicates(tmp_path: Path) -> None:
    p = tmp_path / "s.md"
    p.write_text("- C001: bir\n- C001: iki\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="tekrar eden"):
        load_sentences(p)


def test_load_sentences_rejects_empty(tmp_path: Path) -> None:
    p = tmp_path / "s.md"
    p.write_text("# başlık\nserbest metin\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="bulunamadı"):
        load_sentences(p)


# ------------------------------------------------------------------------ wav
def test_wav_roundtrip_is_16k_mono(tmp_path: Path) -> None:
    path = tmp_path / "a.wav"
    write_wav_pcm16(path, tone(0.5), 16000)
    samples, rate = read_wav_pcm16(path)
    assert rate == 16000 and len(samples) == 8000
    assert max(abs(s) for s in samples) == pytest.approx(0.3, abs=0.01)
    assert not list(tmp_path.glob("*.tmp"))


def test_wav_clamps_out_of_range_samples(tmp_path: Path) -> None:
    path = tmp_path / "b.wav"
    write_wav_pcm16(path, [2.0, -2.0, 0.0], 16000)
    samples, _ = read_wav_pcm16(path)
    assert samples[0] == pytest.approx(1.0) and samples[1] == pytest.approx(-1.0)


# -------------------------------------------------------------------- bayraklar
def test_quality_flags() -> None:
    assert quality_flags(tone()) == ["ok"]
    assert quality_flags([1.0] * 100) == ["clipping"]
    assert quality_flags(tone(), environment="noisy") == ["noise"]
    assert "ok" not in quality_flags([1.0] * 100, environment="noisy")


# ------------------------------------------------------------------ doğrulama
@pytest.mark.parametrize(
    "kw, msg",
    [
        ({"speaker_id": "melike"}, "Konuşmacı kodu"),
        ({"session_id": "1"}, "Oturum kodu"),
        ({"split": "dev"}, "split"),
        ({"consent": "  "}, "consent_or_license"),
    ],
)
def test_session_rejects_bad_metadata(tmp_path: Path, kw: dict, msg: str) -> None:
    with pytest.raises(ValidationError, match=msg):
        make_session(tmp_path, **kw)


# ----------------------------------------------------------------------- kayıt
def test_save_writes_schema_only_manifest_and_sidecar(tmp_path: Path) -> None:
    s = make_session(tmp_path, device="dahili mikrofon")
    rec = s.save(Sentence("C001", "görev ekle"), tone(2.0))

    assert set(rec) == SCHEMA_FIELDS, "manifest şemasına alan eklenmemeli (protokol)"
    assert rec["sample_id"] == "spk_01_s01_C001_t01"
    assert rec["duration_s"] == pytest.approx(2.0)
    assert rec["quality_flags"] == ["ok"]
    assert Path(str(rec["audio_path"])).exists()

    line = json.loads(s.manifest_path.read_text(encoding="utf-8").strip())
    assert line == rec

    rows = list(csv.DictReader(s.sidecar_path.open(encoding="utf-8")))
    assert rows[0]["sentence_id"] == "C001"
    assert rows[0]["verified"] == "no"
    assert rows[0]["device"] == "dahili mikrofon"


def test_takes_increment_and_resume_skips_recorded(tmp_path: Path) -> None:
    sentences = [Sentence("C001", "bir"), Sentence("C002", "iki")]
    s = make_session(tmp_path)
    s.save(sentences[0], tone(0.5))
    s.save(sentences[0], tone(0.5))  # ikinci tekrar
    assert s.next_take("C001") == 3
    assert [x.id for x in s.pending(sentences)] == ["C002"]

    reopened = make_session(tmp_path)  # oturum yeniden açıldı
    assert [x.id for x in reopened.pending(sentences)] == ["C002"]
    assert reopened.next_take("C001") == 3


def test_corrupt_manifest_is_reported(tmp_path: Path) -> None:
    m = tmp_path / "manifests" / "asr_spk_01_real.jsonl"
    m.parent.mkdir(parents=True)
    m.write_text("{bozuk\n", encoding="utf-8")
    with pytest.raises(StoreError, match="bozuk"):
        make_session(tmp_path, manifest_path=m)


# ------------------------------------------------------------- doğrulama turu
def test_update_transcript_and_drop_sample(tmp_path: Path) -> None:
    s = make_session(tmp_path)
    a = s.save(Sentence("C001", "görev ekle"), tone(0.5))
    b = s.save(Sentence("C002", "not al"), tone(0.5))

    update_transcript(s.manifest_path, str(a["sample_id"]), "görev ekle lütfen")
    recs = [json.loads(x) for x in s.manifest_path.read_text(encoding="utf-8").splitlines()]
    assert recs[0]["transcript"] == "görev ekle lütfen"

    drop_sample(s.manifest_path, str(b["sample_id"]))
    recs = [json.loads(x) for x in s.manifest_path.read_text(encoding="utf-8").splitlines()]
    assert [r["sample_id"] for r in recs] == [a["sample_id"]]
    assert not Path(str(b["audio_path"])).exists()

    with pytest.raises(ValidationError, match="bulunamadı"):
        update_transcript(s.manifest_path, "yok", "x")
    with pytest.raises(ValidationError, match="boş olamaz"):
        update_transcript(s.manifest_path, str(a["sample_id"]), "   ")


def test_mark_verified_updates_sidecar(tmp_path: Path) -> None:
    s = make_session(tmp_path)
    rec = s.save(Sentence("C001", "görev ekle"), tone(0.5))
    mark_verified(s.sidecar_path, str(rec["sample_id"]))
    rows = list(csv.DictReader(s.sidecar_path.open(encoding="utf-8")))
    assert rows[0]["verified"] == "yes"


# ------------------------------------------------- üretilen manifest geçerli mi
def test_generated_manifest_passes_project_validator(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "experiments" / "asr"))
    from validate_manifest import validate

    train = make_session(tmp_path, speaker_id="spk_01", split="train")
    train.save(Sentence("C001", "görev ekle"), tone(1.5))
    test = make_session(
        tmp_path,
        speaker_id="spk_07",
        split="test",
        manifest_path=tmp_path / "manifests" / "asr_spk_07_real.jsonl",
    )
    test.save(Sentence("C001", "görev ekle"), tone(1.5))

    rep = validate([train.manifest_path, test.manifest_path], check_files=True)
    assert rep.ok, rep.errors
    assert rep.n == 2 and rep.per_split == {"train": 1, "test": 1}
