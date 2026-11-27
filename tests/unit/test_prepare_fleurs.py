"""FLEURS hazırlama betiği: biçim dönüşümü ve manifest sözleşmesi.

Gerçek veri gerektirmez; FLEURS'ün dağıttığı düzen (başlıksız TSV + 32 bit float
WAV) küçük ölçekte taklit edilir. soundfile kurulu değilse (CI'ın öntanımlı
ortamı) testler atlanır.
"""

import json
import sys
from pathlib import Path

import pytest

sf = pytest.importorskip("soundfile", reason="soundfile yalnızca audio/train ekstralarında")
np = pytest.importorskip("numpy")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "asr"))

import prepare_fleurs as P  # noqa: E402

RATE = 16_000


def _write_float_wav(path: Path, seconds: float) -> None:
    """FLEURS'teki gibi 32 bit float, 16 kHz, tek kanal yazar."""
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = np.zeros(int(RATE * seconds), dtype="float32")
    sf.write(str(path), samples, RATE, subtype="FLOAT")


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    """İki satırlık sahte bir FLEURS test bölmesi."""
    rows = [
        (
            "1690",
            "a.wav",
            "Birinci cümle, noktalamalı.",
            "birinci cümle noktalamalı",
            "b",
            "32000",
            "MALE",
        ),
        ("1821", "b.wav", "İkinci cümle.", "ikinci cümle", "i", "16000", "FEMALE"),
    ]
    (tmp_path / "test.tsv").write_text(
        "\n".join("\t".join(r) for r in rows) + "\n", encoding="utf-8"
    )
    _write_float_wav(tmp_path / "test" / "a.wav", 2.0)
    _write_float_wav(tmp_path / "test" / "b.wav", 1.0)
    return tmp_path


def test_reads_rows_with_existing_audio(dataset: Path) -> None:
    utterances = P.read_split(dataset, "test")
    assert [u.filename for u in utterances] == ["a.wav", "b.wav"]
    assert utterances[0].transcript == "Birinci cümle, noktalamalı."
    assert utterances[0].duration_s == pytest.approx(2.0)


def test_skips_rows_whose_audio_is_missing(dataset: Path) -> None:
    (dataset / "test" / "b.wav").unlink()
    assert [u.filename for u in P.read_split(dataset, "test")] == ["a.wav"]


def test_output_is_pcm16_even_though_source_is_float(dataset: Path, tmp_path: Path) -> None:
    """Protokol PCM-16 istiyor; FLEURS float dağıtıyor. Dönüşüm yapılmazsa eğitim hattı bozulur."""
    utterances = P.read_split(dataset, "test")
    audio_root = tmp_path / "out_audio"
    P.write_split("test", utterances, audio_root, tmp_path / "out_manifests")
    produced = sorted(audio_root.glob("test/*.wav"))
    assert len(produced) == 2
    for path in produced:
        info = sf.info(str(path))
        assert info.subtype == "PCM_16"
        assert info.samplerate == RATE
        assert info.channels == 1


def test_manifest_matches_protocol_schema(dataset: Path, tmp_path: Path) -> None:
    utterances = P.read_split(dataset, "test")
    manifest_root = tmp_path / "out_manifests"
    count, total = P.write_split("test", utterances, tmp_path / "out_audio", manifest_root)
    assert count == 2
    assert total == pytest.approx(3.0)

    lines = (manifest_root / "asr_test_real.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines]
    assert len(rows) == 2
    for row in rows:
        assert set(row) == {
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
        assert row["source"] == "fleurs_tr"
        assert row["consent_or_license"] == "CC-BY-4.0"
        assert row["language"] == "tr"


def test_unknown_speaker_is_declared_not_invented(dataset: Path, tmp_path: Path) -> None:
    """FLEURS konuşmacı kimliği vermiyor; uydurmak yerine açıkça işaretlenmeli."""
    utterances = P.read_split(dataset, "test")
    manifest_root = tmp_path / "out_manifests"
    P.write_split("test", utterances, tmp_path / "out_audio", manifest_root)
    rows = [
        json.loads(line)
        for line in (manifest_root / "asr_test_real.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    for row in rows:
        assert row["speaker_id"] == "unknown"
        assert "no_speaker_id" in row["quality_flags"]


def test_sample_ids_are_stable_and_unique(dataset: Path, tmp_path: Path) -> None:
    """Aynı girdi aynı kimliği üretmeli; ölçüm tekrarlanabilirliği buna bağlı."""
    utterances = P.read_split(dataset, "test")
    first = tmp_path / "a"
    second = tmp_path / "b"
    P.write_split("test", utterances, first / "audio", first)
    P.write_split("test", utterances, second / "audio", second)
    ids_a = [
        json.loads(line)["sample_id"]
        for line in (first / "asr_test_real.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    ids_b = [
        json.loads(line)["sample_id"]
        for line in (second / "asr_test_real.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert ids_a == ids_b
    assert len(set(ids_a)) == len(ids_a)


def test_limit_by_hours_keeps_budget(dataset: Path) -> None:
    utterances = P.read_split(dataset, "test")
    kept = P.limit_by_hours(utterances, 2.0 / 3600)  # 2 saniyelik bütçe
    assert [u.filename for u in kept] == ["a.wav"]
    assert P.limit_by_hours(utterances, None) == utterances
