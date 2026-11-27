"""Common Voice Türkçe'den konuşmacı-ayrık ASR alt kümeleri hazırlar.

Mozilla Data Collective'den indirilmiş ve açılmış bir Common Voice paketini
girdi olarak alır. Arşivi kendisi indirmez; seçilecek örneklerden fazlasını
önceden indirmemek için kaynak erişimi kullanıcı tarafından yapılmalıdır.

Örnek:
  uv run python experiments/asr/prepare_common_voice.py \
    --dataset-dir /path/to/cv-corpus-27.0/tr

Gereksinim: ffmpeg ve ffprobe PATH üzerinde olmalıdır.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Clip:
    client_id: str
    filename: str
    transcript: str
    source_path: Path


def probe_duration(path: Path) -> float:
    """Klibin süresini ffprobe ile okur."""
    # Komut sabittir ve kabuk kullanılmaz; kullanıcı girdisi yalnızca dosya yolu
    # olarak geçer. ffprobe PATH üzerinden çözülür, varlığı main() içinde denetlenir.
    cmd = [  # noqa: S607
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603
    return float(result.stdout.strip())


def convert_clip(source: Path, target: Path) -> None:
    """Klibi protokoldeki biçime çevirir: 16 kHz, tek kanal, 16-bit PCM WAV."""
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [  # noqa: S607
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(target),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)  # noqa: S603


def read_clips(dataset_dir: Path, metadata: Path, clips_dir: Path) -> dict[str, list[Clip]]:
    grouped: dict[str, list[Clip]] = defaultdict(list)
    metadata_path = dataset_dir / metadata
    source_clips_dir = dataset_dir / clips_dir
    with metadata_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file, delimiter="\t")
        required = {"client_id", "path", "sentence"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"{metadata_path}: client_id, path, sentence sütunları gerekli")
        for row in reader:
            client_id = (row.get("client_id") or "").strip()
            filename = Path(row.get("path") or "").name
            transcript = (row.get("sentence") or "").strip()
            source_path = source_clips_dir / filename
            if client_id and filename and transcript and source_path.is_file():
                grouped[client_id].append(Clip(client_id, filename, transcript, source_path))
    return grouped


def sample_split(
    split: str,
    target_s: float,
    speakers: list[str],
    grouped: dict[str, list[Clip]],
    rng: random.Random,
    max_speaker_s: float,
) -> tuple[list[tuple[Clip, float]], list[str], float]:
    selected: list[tuple[Clip, float]] = []
    used_speakers: list[str] = []
    total_s = 0.0
    while speakers and total_s < target_s:
        speaker = speakers.pop()
        candidates = grouped[speaker].copy()
        rng.shuffle(candidates)
        speaker_s = 0.0
        for clip in candidates:
            if total_s >= target_s or speaker_s >= max_speaker_s:
                break
            duration_s = probe_duration(clip.source_path)
            if not 0.3 <= duration_s <= 30.0:
                continue
            if speaker_s + duration_s > max_speaker_s:
                continue
            selected.append((clip, duration_s))
            total_s += duration_s
            speaker_s += duration_s
        if speaker_s:
            used_speakers.append(speaker)
    if total_s < target_s:
        print(
            f"UYARI: {split} hedefi {target_s / 3600:.2f} saat; bulunan {total_s / 3600:.2f} saat.",
            file=sys.stderr,
        )
    return selected, used_speakers, total_s


def repo_relative(path: Path) -> str:
    """Manifest yolunu depo köküne göre göreli yazar.

    Veri hazırlığı ile eğitim farklı makinelerde yapılabildiği için mutlak yol
    taşınabilir değildir (ör. macOS'ta hazırlanan manifest Windows'ta çalışmaz).
    Depo kökünün dışındaki yollar olduğu gibi bırakılır.
    """
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def write_split(
    split: str,
    selected: list[tuple[Clip, float]],
    audio_root: Path,
    manifest_root: Path,
) -> None:
    manifest_root.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_root / f"asr_{split}_real.jsonl"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as manifest:
        for clip, duration_s in selected:
            sample_hash = hashlib.sha256(f"{clip.client_id}\0{clip.filename}".encode()).hexdigest()[
                :16
            ]
            sample_id = f"cvtr_{sample_hash}"
            audio_path = audio_root / split / f"{sample_id}.wav"
            convert_clip(clip.source_path, audio_path)
            row = {
                "sample_id": sample_id,
                "audio_path": repo_relative(audio_path),
                "transcript": clip.transcript,
                "speaker_id": clip.client_id,
                "language": "tr",
                "duration_s": round(duration_s, 4),
                "split": split,
                "source": "common_voice_tr",
                "consent_or_license": "CC0-1.0",
                "quality_flags": [
                    "ok"
                ],  # protokol: normal kayıt; sorunlu olanlar süre filtresinde elenir
            }
            manifest.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, default=Path("validated.tsv"))
    parser.add_argument("--clips-dir", type=Path, default=Path("clips"))
    parser.add_argument("--audio-root", type=Path, default=Path("datasets/audio/common_voice_tr"))
    parser.add_argument("--manifest-root", type=Path, default=Path("datasets/manifests"))
    parser.add_argument("--train-hours", type=float, default=2.5)
    parser.add_argument("--val-hours", type=float, default=0.5)
    parser.add_argument("--test-hours", type=float, default=0.5)
    parser.add_argument("--max-speaker-minutes", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        parser.error("ffmpeg ve ffprobe PATH üzerinde bulunmalı")
    metadata_path = args.dataset_dir / args.metadata
    if not metadata_path.is_file():
        parser.error(f"metadata bulunamadı: {metadata_path}")
    clips = read_clips(args.dataset_dir, args.metadata, args.clips_dir)
    speakers = list(clips)
    # Kriptografik amaç yok; --seed ile tekrarlanabilir örnekleme isteniyor.
    rng = random.Random(args.seed)  # noqa: S311
    rng.shuffle(speakers)
    max_speaker_s = args.max_speaker_minutes * 60
    if max_speaker_s <= 0:
        parser.error("--max-speaker-minutes pozitif olmalı")

    for split, target_hours in (
        ("train", args.train_hours),
        ("val", args.val_hours),
        ("test", args.test_hours),
    ):
        if target_hours <= 0:
            parser.error("hedef saatler pozitif olmalı")
        selected, used_speakers, total_s = sample_split(
            split, target_hours * 3600, speakers, clips, rng, max_speaker_s
        )
        write_split(split, selected, args.audio_root, args.manifest_root)
        print(
            f"{split}: {len(selected)} örnek, {len(used_speakers)} konuşmacı, "
            f"{total_s / 3600:.2f} saat"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
