"""ASR manifestini şema, dosya ve split kurallarına göre doğrular (model gerektirmez).

Kullanım:
  uv run python experiments/asr/validate_manifest.py datasets/manifests/asr_synthetic_example.jsonl
  uv run python experiments/asr/validate_manifest.py train.jsonl val.jsonl test.jsonl --check-files

Kontroller: zorunlu alanlar, split değeri, süre aralığı, boş transkript, konuşmacı sızıntısı
(aynı speaker_id birden fazla split'te), tekrar eden sample_id, izin alanı boş mu, dosya var mı.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED = (
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
)
SPLITS = {"train", "val", "test"}
MIN_DUR, MAX_DUR = 0.3, 30.0


@dataclass
class Report:
    n: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    per_split: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    speakers_per_split: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    total_duration_s: float = 0.0

    @property
    def ok(self) -> bool:
        return not self.errors


def validate(paths: list[Path], check_files: bool = False) -> Report:
    rep = Report()
    seen_ids: set[str] = set()
    for path in paths:
        if not path.exists():
            rep.errors.append(f"{path}: dosya yok")
            continue
        for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            where = f"{path.name}:{ln}"
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                rep.errors.append(f"{where}: geçersiz JSON ({exc.msg})")
                continue
            rep.n += 1
            missing = [k for k in REQUIRED if k not in row]
            if missing:
                rep.errors.append(f"{where}: eksik alan {missing}")
                continue
            sid = row["sample_id"]
            if sid in seen_ids:
                rep.errors.append(f"{where}: tekrar eden sample_id {sid!r}")
            seen_ids.add(sid)
            if row["split"] not in SPLITS:
                rep.errors.append(f"{where}: split {row['split']!r} ∉ {sorted(SPLITS)}")
            if not str(row["transcript"]).strip():
                rep.errors.append(f"{where}: boş transkript")
            if row["language"] != "tr":
                rep.warnings.append(f"{where}: language={row['language']!r} (tr bekleniyor)")
            try:
                dur = float(row["duration_s"])
            except (TypeError, ValueError):
                rep.errors.append(f"{where}: duration_s sayı değil")
                dur = 0.0
            if not MIN_DUR <= dur <= MAX_DUR:
                rep.warnings.append(f"{where}: süre {dur}s aralık dışı [{MIN_DUR},{MAX_DUR}]")
            if not str(row["consent_or_license"]).strip():
                rep.errors.append(f"{where}: consent_or_license boş — izinsiz veri kullanılamaz")
            if not isinstance(row["quality_flags"], list):
                rep.errors.append(f"{where}: quality_flags liste olmalı")
            if check_files and not Path(row["audio_path"]).exists():
                rep.errors.append(f"{where}: ses dosyası yok {row['audio_path']}")
            rep.per_split[row["split"]] += 1
            rep.speakers_per_split[row["split"]].add(row["speaker_id"])
            rep.total_duration_s += dur

    # Konuşmacı sızıntısı
    splits = list(rep.speakers_per_split)
    for i, a in enumerate(splits):
        for b in splits[i + 1 :]:
            leak = rep.speakers_per_split[a] & rep.speakers_per_split[b]
            if leak:
                rep.errors.append(f"konuşmacı sızıntısı {a}∩{b}: {sorted(leak)}")
    return rep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifests", nargs="+", type=Path)
    ap.add_argument(
        "--check-files", action="store_true", help="audio_path dosyalarının varlığını denetle"
    )
    args = ap.parse_args()
    rep = validate(args.manifests, args.check_files)
    print(f"örnek: {rep.n}  toplam süre: {rep.total_duration_s / 60:.1f} dk")
    for s in sorted(rep.per_split):
        print(f"  {s:5}: {rep.per_split[s]:4} örnek, {len(rep.speakers_per_split[s])} konuşmacı")
    for w in rep.warnings:
        print("UYARI:", w)
    for e in rep.errors:
        print("HATA :", e)
    print("SONUÇ:", "geçerli" if rep.ok else f"{len(rep.errors)} hata")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
