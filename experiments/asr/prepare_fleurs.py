"""FLEURS Türkçe'den ASR manifestleri hazırlar (ADR-010 yedek kaynağı).

Common Voice Ekim 2025'te Hugging Face'ten kaldırılıp Mozilla Data Collective'e
taşındığı ve hesapla manuel indirme gerektirdiği için uyarlama verisi olarak
FLEURS (CC-BY-4.0) kullanılır. FLEURS sesleri 16 kHz tek kanaldır ama **32 bit
float** WAV olarak dağıtılır; protokol PCM-16 istediği için örnekler okunup yeniden
yazılır. Dönüşüm soundfile ile yapılır, **ffmpeg gerekmez** (bu makinede bozuk).

**Konuşmacı kimliği uyarısı:** FLEURS konuşmacı kimliği yayımlamaz. Resmî
train/dev/test bölmeleri konuşmacı-ayrık kabul edilir, ancak bunu veriden
doğrulayamayız. Manifestte `speaker_id` alanı `unknown` yazılır ve
`quality_flags` içine `no_speaker_id` konur; uydurma kimlik üretilmez.
Doğrulayıcı bu durumda sızıntı denetimini atlar ve uyarı basar.

Örnek:
  uv run python experiments/asr/prepare_fleurs.py --dataset-dir datasets/raw/fleurs_tr
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

import soundfile as sf

SAMPLE_RATE = 16_000
CHANNELS = 1
LICENSE = "CC-BY-4.0"
SOURCE = "fleurs_tr"
UNKNOWN_SPEAKER = "unknown"

# TSV sütunları (başlıksız): id, dosya adı, ham metin, normalize metin,
# karakter dizisi, örnek sayısı, cinsiyet.
COL_FILENAME = 1
COL_RAW_TEXT = 2
COL_NUM_SAMPLES = 5
MIN_COLUMNS = 6


@dataclass(frozen=True)
class Utterance:
    filename: str
    transcript: str
    source_path: Path
    duration_s: float


def repo_relative(path: Path) -> str:
    """Manifest yolunu depo köküne göre göreli yazar; mutlak yol taşınmaz."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def ensure_extracted(dataset_dir: Path, split: str) -> Path:
    """Bölmenin ses dizinini döndürür; yalnızca arşiv varsa açar."""
    split_dir = dataset_dir / split
    if split_dir.is_dir():
        return split_dir
    archive = dataset_dir / f"{split}.tar.gz"
    if not archive.is_file():
        raise FileNotFoundError(f"{split_dir} de {archive} de yok")
    print(f"  {archive.name} açılıyor…", file=sys.stderr)
    with tarfile.open(archive) as tar:
        tar.extractall(dataset_dir, filter="data")
    if not split_dir.is_dir():
        raise FileNotFoundError(f"{archive.name} açıldı ama {split_dir} oluşmadı")
    return split_dir


def read_audio_meta(path: Path) -> tuple[int, int, float]:
    """(kanal, örnekleme hızı, süre) döndürür."""
    info = sf.info(str(path))
    duration = info.frames / info.samplerate if info.samplerate else 0.0
    return info.channels, info.samplerate, duration


def convert_to_pcm16(source: Path, target: Path) -> None:
    """Protokoldeki biçime yazar: 16 kHz, tek kanal, PCM-16 WAV.

    FLEURS 32 bit float dağıtır; faster-whisper float kabul etse de manifest
    sözleşmesi PCM-16 diyor ve eğitim hattı da bunu bekliyor.
    """
    data, rate = sf.read(str(source), dtype="float32", always_2d=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(target), data, rate, subtype="PCM_16")


def read_split(dataset_dir: Path, split: str) -> list[Utterance]:
    """Bölmenin TSV'sini okur, ses dosyası bulunan ve biçimi doğru satırları döndürür."""
    tsv_path = dataset_dir / f"{split}.tsv"
    if not tsv_path.is_file():
        raise FileNotFoundError(f"{tsv_path} yok")
    audio_dir = ensure_extracted(dataset_dir, split)

    utterances: list[Utterance] = []
    missing = 0
    malformed = 0
    seen: set[str] = set()
    with tsv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) <= MIN_COLUMNS:
                malformed += 1
                continue
            filename = row[COL_FILENAME].strip()
            transcript = row[COL_RAW_TEXT].strip()
            if not filename or not transcript or filename in seen:
                malformed += 1
                continue
            source_path = audio_dir / filename
            if not source_path.is_file():
                missing += 1
                continue
            channels, rate, duration = read_audio_meta(source_path)
            if (channels, rate) != (CHANNELS, SAMPLE_RATE):
                print(
                    f"  UYARI: {filename} beklenen biçimde değil "
                    f"({channels} kanal, {rate} Hz) — atlandı",
                    file=sys.stderr,
                )
                malformed += 1
                continue
            seen.add(filename)
            utterances.append(Utterance(filename, transcript, source_path, duration))

    if missing:
        print(f"  {missing} satırın ses dosyası bulunamadı, atlandı", file=sys.stderr)
    if malformed:
        print(f"  {malformed} satır biçim denetiminden geçmedi, atlandı", file=sys.stderr)
    return utterances


def limit_by_hours(utterances: list[Utterance], max_hours: float | None) -> list[Utterance]:
    """Süre sınırı verilmişse TSV sırasını koruyarak keser (rastgelelik yok)."""
    if max_hours is None:
        return utterances
    budget = max_hours * 3600
    kept: list[Utterance] = []
    total = 0.0
    for utterance in utterances:
        if total + utterance.duration_s > budget:
            break
        kept.append(utterance)
        total += utterance.duration_s
    return kept


def write_split(
    split: str,
    utterances: list[Utterance],
    audio_root: Path,
    manifest_root: Path,
) -> tuple[int, float]:
    """Sesleri kopyalar, manifesti yazar; (örnek sayısı, toplam süre) döndürür."""
    manifest_root.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_root / f"asr_{split}_real.jsonl"
    total = 0.0
    with manifest_path.open("w", encoding="utf-8", newline="\n") as manifest:
        for utterance in utterances:
            digest = hashlib.sha256(utterance.filename.encode()).hexdigest()[:16]
            sample_id = f"fleurs_{digest}"
            audio_path = audio_root / split / f"{sample_id}.wav"
            convert_to_pcm16(utterance.source_path, audio_path)
            row = {
                "sample_id": sample_id,
                "audio_path": repo_relative(audio_path),
                "transcript": utterance.transcript,
                "speaker_id": UNKNOWN_SPEAKER,
                "language": "tr",
                "duration_s": round(utterance.duration_s, 4),
                "split": split,
                "source": SOURCE,
                "consent_or_license": LICENSE,
                # no_speaker_id: FLEURS konuşmacı kimliği yayımlamıyor; sızıntı
                # denetimi veriden doğrulanamıyor, resmî bölmelere güveniliyor.
                "quality_flags": ["ok", "no_speaker_id"],
            }
            manifest.write(json.dumps(row, ensure_ascii=False) + "\n")
            total += utterance.duration_s
    return len(utterances), total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("datasets/raw/fleurs_tr"),
        help="FLEURS tr_tr dosyalarının bulunduğu dizin (TSV + tar.gz ya da açılmış dizinler)",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["test", "dev"],
        choices=["train", "dev", "test"],
        help="hazırlanacak bölmeler (öntanımlı: test dev)",
    )
    parser.add_argument(
        "--max-hours",
        type=float,
        default=None,
        help="her bölme için süre sınırı (TSV sırası korunur; rastgele örnekleme yok)",
    )
    parser.add_argument("--audio-root", type=Path, default=Path("datasets/audio/fleurs_tr"))
    parser.add_argument("--manifest-root", type=Path, default=Path("datasets/manifests"))
    args = parser.parse_args()

    if not args.dataset_dir.is_dir():
        print(
            f"HATA: {args.dataset_dir} yok. FLEURS tr_tr dosyalarını oraya indirin.",
            file=sys.stderr,
        )
        return 2

    # FLEURS bölme adı manifestteki split adıyla birebir eşleşir; dev → val eşlemesi
    # yapılmaz çünkü train_whisper.py val manifestini adıyla arar.
    split_names = {"train": "train", "dev": "val", "test": "test"}

    print(f"FLEURS Türkçe hazırlanıyor: {args.dataset_dir}", file=sys.stderr)
    summary: list[tuple[str, int, float]] = []
    for split in args.splits:
        print(f"[{split}] okunuyor…", file=sys.stderr)
        utterances = limit_by_hours(read_split(args.dataset_dir, split), args.max_hours)
        if not utterances:
            print(f"HATA: {split} bölmesinde kullanılabilir örnek yok", file=sys.stderr)
            return 1
        count, total = write_split(
            split_names[split], utterances, args.audio_root, args.manifest_root
        )
        summary.append((split_names[split], count, total))

    print("\nÖzet", file=sys.stderr)
    for name, count, total in summary:
        print(f"  {name:5}: {count:4} örnek, {total / 3600:.2f} saat", file=sys.stderr)
    print(
        "\nUYARI: FLEURS konuşmacı kimliği yayımlamıyor. speaker_id alanı 'unknown' "
        "yazıldı; konuşmacı-ayrıklık resmî bölmelere dayanıyor, veriden doğrulanmadı. "
        "Bunu raporda belirtin.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
