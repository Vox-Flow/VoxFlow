"""Common Voice hazırlama betiğinin örnekleme mantığı.

ffmpeg/ffprobe gerektirmez: süre okuma sahte bir işlevle değiştirilir, böylece
testler CI'da ve ses araçları kurulu olmayan makinelerde de koşar.
"""

import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "asr"))

import prepare_common_voice as P  # noqa: E402


@pytest.fixture
def grouped() -> dict[str, list]:
    """Yirmi konuşmacı, her birinde otuzar klip."""
    return {
        f"client_{s:02d}": [
            P.Clip(f"client_{s:02d}", f"s{s}_{i}.mp3", f"cümle {s}-{i}", Path(f"/yok/s{s}_{i}.mp3"))
            for i in range(30)
        ]
        for s in range(1, 21)
    }


@pytest.fixture(autouse=True)
def fake_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """ffprobe yerine dosya adından türetilen sabit süre."""
    monkeypatch.setattr(P, "probe_duration", lambda path: 1.0 + (len(path.name) % 4))


def _split_all(grouped: dict[str, list], targets=(600, 120, 120)):  # type: ignore[no-untyped-def]
    speakers = list(grouped)
    rng = random.Random(42)
    rng.shuffle(speakers)
    out = {}
    for split, target in zip(("train", "val", "test"), targets, strict=True):
        selected, used, total = P.sample_split(split, target, speakers, grouped, rng, 120)
        out[split] = (selected, set(used), total)
    return out


def test_splits_are_speaker_disjoint(grouped: dict[str, list]) -> None:
    """Aynı konuşmacı iki bölmede yer alamaz — genelleme ölçümü için şart."""
    res = _split_all(grouped)
    train, val, test = (res[k][1] for k in ("train", "val", "test"))
    assert train and val and test
    assert not (train & val)
    assert not (train & test)
    assert not (val & test)


def test_selected_clips_belong_to_their_split_speakers(grouped: dict[str, list]) -> None:
    res = _split_all(grouped)
    for _split, (selected, used, _total) in res.items():
        assert {clip.client_id for clip, _ in selected} <= used


def test_per_speaker_cap_is_respected(grouped: dict[str, list]) -> None:
    """Tek konuşmacı bölmeye hâkim olmamalı."""
    speakers = list(grouped)
    rng = random.Random(7)
    selected, _used, _total = P.sample_split("train", 3600, speakers, grouped, rng, 60)
    per_speaker: dict[str, float] = {}
    for clip, duration in selected:
        per_speaker[clip.client_id] = per_speaker.get(clip.client_id, 0.0) + duration
    assert per_speaker and max(per_speaker.values()) <= 60


def test_warns_when_target_not_reachable(
    grouped: dict[str, list], capsys: pytest.CaptureFixture[str]
) -> None:
    speakers = list(grouped)[:1]
    P.sample_split("test", 10_000, speakers, grouped, random.Random(1), 60)
    assert "UYARI" in capsys.readouterr().err


def test_repo_relative_path_is_portable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Manifest yolu depo köküne göre göreli olmalı; mutlak yol makineler arası taşınmaz."""
    monkeypatch.chdir(tmp_path)
    inside = tmp_path / "datasets" / "audio" / "x.wav"
    assert P.repo_relative(inside) == str(Path("datasets/audio/x.wav"))
    # Kök dışındaki dosya göreliye çevrilemez; mutlak yol olduğu gibi kalır.
    # (tmp_path.parent, cwd'nin dışında olduğu garanti edilen tek yol.)
    outside = tmp_path.parent / "disarida" / "x.wav"
    assert Path(P.repo_relative(outside)).is_absolute()
