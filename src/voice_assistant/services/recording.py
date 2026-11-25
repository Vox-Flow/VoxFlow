"""Veri toplama oturumu: cümle listesi, WAV yazımı, ASR manifesti ve yerel çizelge.

Protokol: `docs/dataset_protocol.md` (#17 bölümü). Tasarım kararları:
- Manifest **tam olarak** şemadaki 10 alanı içerir; cümle kimliği ve kontrol durumu
  protokolün istediği gibi ayrı yerel çizelgede (`session_<id>.csv`) tutulur.
- `consent_or_license` asla otomatik doldurulmaz; operatör açıkça belirtir.
- WAV yazımı standart kütüphane ile yapılır (16 kHz mono PCM-16), böylece bu modül
  numpy/soundfile olmadan da test edilebilir.
"""

from __future__ import annotations

import csv
import json
import re
import wave
from array import array
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from voice_assistant.domain.errors import StoreError, ValidationError

SENTENCE_RE = re.compile(r"^-\s*(?P<id>C\d{3})\s*:\s*(?P<text>.+?)\s*$")
SPEAKER_RE = re.compile(r"^spk_\d{2,3}$")
SESSION_RE = re.compile(r"^s\d{2}$")
CLIP_LEVEL = 0.99
CLIP_RATIO_FLAG = 0.001  # örneklerin %0.1'i tam ölçekteyse "clipping"
SIDECAR_FIELDS = (
    "sample_id",
    "sentence_id",
    "take",
    "duration_s",
    "quality_flags",
    "environment",
    "device",
    "verified",
    "recorded_at",
    "note",
)


@dataclass(frozen=True)
class Sentence:
    """Okuma listesindeki tek satır."""

    id: str
    text: str


def load_sentences(path: Path) -> list[Sentence]:
    """`- C001: metin` biçimindeki satırları okur. Başlıklar ve açıklamalar atlanır."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(f"Cümle listesi okunamadı: {path} ({exc})") from exc
    out: list[Sentence] = []
    seen: set[str] = set()
    for line in lines:
        m = SENTENCE_RE.match(line)
        if not m:
            continue
        sid = m.group("id")
        if sid in seen:
            raise ValidationError(f"Cümle listesinde tekrar eden kimlik: {sid}")
        seen.add(sid)
        out.append(Sentence(sid, m.group("text")))
    if not out:
        raise ValidationError(f"{path} içinde '- C001: metin' biçiminde cümle bulunamadı.")
    return out


def write_wav_pcm16(path: Path, samples: Iterable[float], sample_rate: int) -> None:
    """16-bit PCM, tek kanal WAV yazar (numpy/soundfile gerektirmez)."""
    pcm = array("h", (int(max(-1.0, min(1.0, float(s))) * 32767) for s in samples))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".wav.tmp")
    try:
        with wave.open(str(tmp), "wb") as fh:
            fh.setnchannels(1)
            fh.setsampwidth(2)
            fh.setframerate(sample_rate)
            fh.writeframes(pcm.tobytes())
        tmp.replace(path)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise StoreError(f"WAV yazılamadı: {path} ({exc})") from exc


def read_wav_pcm16(path: Path) -> tuple[list[float], int]:
    """Yazdığımız WAV'ı geri okur (doğrulama turu ve testler için)."""
    with wave.open(str(path), "rb") as fh:
        if fh.getsampwidth() != 2 or fh.getnchannels() != 1:
            raise ValidationError(f"{path}: 16-bit tek kanal WAV bekleniyor.")
        raw = fh.readframes(fh.getnframes())
        rate = fh.getframerate()
    pcm = array("h")
    pcm.frombytes(raw)
    return [s / 32767 for s in pcm], rate


def quality_flags(samples: Sequence[float], environment: str = "quiet") -> list[str]:
    """Protokoldeki bayraklar. 'ok' başka bayrakla birlikte verilmez."""
    flags: list[str] = []
    if samples:
        clipped = sum(1 for s in samples if abs(s) >= CLIP_LEVEL) / len(samples)
        if clipped > CLIP_RATIO_FLAG:
            flags.append("clipping")
    if environment == "noisy":
        flags.append("noise")
    return flags or ["ok"]


@dataclass
class RecordingSession:
    """Tek konuşmacı-oturum için dosya adları, manifest ve çizelge yönetimi."""

    speaker_id: str
    session_id: str
    split: str
    consent: str
    audio_root: Path
    manifest_path: Path
    environment: str = "quiet"
    device: str = ""
    sample_rate: int = 16000
    language: str = "tr"
    source: str = "team_spoken_transcribed"
    _existing: set[str] = field(default_factory=set, init=False)

    def __post_init__(self) -> None:
        if not SPEAKER_RE.match(self.speaker_id):
            raise ValidationError(f"Konuşmacı kodu 'spk_01' biçiminde olmalı: {self.speaker_id!r}")
        if not SESSION_RE.match(self.session_id):
            raise ValidationError(f"Oturum kodu 's01' biçiminde olmalı: {self.session_id!r}")
        if self.split not in ("train", "val", "test"):
            raise ValidationError(f"split train/val/test olmalı: {self.split!r}")
        if not self.consent.strip():
            raise ValidationError(
                "consent_or_license boş olamaz; açık izin alınmadan kayıt yapılmaz "
                "(docs/consent_form_tr.md)."
            )
        self._existing = self._load_existing_ids()

    # ------------------------------------------------------------------ yollar
    @property
    def speaker_dir(self) -> Path:
        return self.audio_root / self.speaker_id

    @property
    def sidecar_path(self) -> Path:
        return self.speaker_dir / f"session_{self.session_id}.csv"

    def sample_id(self, sentence_id: str, take: int) -> str:
        return f"{self.speaker_id}_{self.session_id}_{sentence_id}_t{take:02d}"

    def audio_path(self, sample_id: str) -> Path:
        return self.speaker_dir / f"{sample_id}.wav"

    # --------------------------------------------------------------- manifest
    def _load_existing_ids(self) -> set[str]:
        if not self.manifest_path.exists():
            return set()
        ids: set[str] = set()
        for line in self.manifest_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ids.add(json.loads(line)["sample_id"])
            except (json.JSONDecodeError, KeyError) as exc:
                raise StoreError(f"{self.manifest_path} bozuk: {exc}") from exc
        return ids

    def next_take(self, sentence_id: str) -> int:
        """Aynı cümle için bir sonraki tekrar numarası (1'den başlar)."""
        prefix = f"{self.speaker_id}_{self.session_id}_{sentence_id}_t"
        takes = [int(i[len(prefix) :]) for i in self._existing if i.startswith(prefix)]
        return max(takes, default=0) + 1

    def is_recorded(self, sentence_id: str) -> bool:
        return self.next_take(sentence_id) > 1

    def pending(self, sentences: Sequence[Sentence]) -> list[Sentence]:
        """Henüz kaydedilmemiş cümleler (oturuma kaldığı yerden devam)."""
        return [s for s in sentences if not self.is_recorded(s.id)]

    # ------------------------------------------------------------------ kayıt
    def save(
        self,
        sentence: Sentence,
        samples: Sequence[float],
        *,
        note: str = "",
    ) -> dict[str, object]:
        """WAV + manifest satırı + çizelge satırı yazar; manifest kaydını döndürür."""
        duration = len(samples) / self.sample_rate if self.sample_rate else 0.0
        take = self.next_take(sentence.id)
        sid = self.sample_id(sentence.id, take)
        path = self.audio_path(sid)
        write_wav_pcm16(path, samples, self.sample_rate)

        record = {
            "sample_id": sid,
            "audio_path": str(path),
            "transcript": sentence.text,
            "speaker_id": self.speaker_id,
            "language": self.language,
            "duration_s": round(duration, 3),
            "split": self.split,
            "source": self.source,
            "consent_or_license": self.consent,
            "quality_flags": quality_flags(samples, self.environment),
        }
        self._append_manifest(record)
        self._append_sidecar(record, sentence_id=sentence.id, take=take, note=note)
        self._existing.add(sid)
        return record

    def _append_manifest(self, record: dict[str, object]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.manifest_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            raise StoreError(f"Manifest yazılamadı: {self.manifest_path} ({exc})") from exc

    def _append_sidecar(
        self, record: dict[str, object], *, sentence_id: str, take: int, note: str
    ) -> None:
        """Cümle kimliği ve kontrol durumu manifestte değil, burada tutulur (protokol)."""
        new = not self.sidecar_path.exists()
        self.sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self.sidecar_path.open("a", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=SIDECAR_FIELDS)
                if new:
                    writer.writeheader()
                writer.writerow(
                    {
                        "sample_id": record["sample_id"],
                        "sentence_id": sentence_id,
                        "take": take,
                        "duration_s": record["duration_s"],
                        "quality_flags": " ".join(record["quality_flags"]),  # type: ignore[arg-type]
                        "environment": self.environment,
                        "device": self.device,
                        "verified": "no",
                        "recorded_at": datetime.now().isoformat(timespec="seconds"),
                        "note": note,
                    }
                )
        except OSError as exc:
            raise StoreError(f"Çizelge yazılamadı: {self.sidecar_path} ({exc})") from exc

    # ------------------------------------------------------------- doğrulama
    def summary(self, sentences: Sequence[Sentence]) -> dict[str, object]:
        done = [s for s in sentences if self.is_recorded(s.id)]
        return {
            "speaker_id": self.speaker_id,
            "session_id": self.session_id,
            "kaydedilen": len(done),
            "toplam": len(sentences),
            "manifest": str(self.manifest_path),
            "cizelge": str(self.sidecar_path),
        }


def update_transcript(manifest_path: Path, sample_id: str, transcript: str) -> None:
    """Doğrulama turunda düzeltilen transkripti manifestte günceller (atomik)."""
    if not transcript.strip():
        raise ValidationError("Transkript boş olamaz.")
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    found = False
    for line in lines:
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec["sample_id"] == sample_id:
            rec["transcript"] = transcript.strip()
            found = True
        out.append(json.dumps(rec, ensure_ascii=False))
    if not found:
        raise ValidationError(f"Manifestte bulunamadı: {sample_id}")
    tmp = manifest_path.with_suffix(".jsonl.tmp")
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    tmp.replace(manifest_path)


def drop_sample(manifest_path: Path, sample_id: str, *, delete_audio: bool = True) -> None:
    """Reddedilen kaydı manifestten çıkarır ve ses dosyasını siler."""
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    removed: dict[str, object] | None = None
    for line in lines:
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec["sample_id"] == sample_id:
            removed = rec
            continue
        out.append(json.dumps(rec, ensure_ascii=False))
    if removed is None:
        raise ValidationError(f"Manifestte bulunamadı: {sample_id}")
    tmp = manifest_path.with_suffix(".jsonl.tmp")
    tmp.write_text(("\n".join(out) + "\n") if out else "", encoding="utf-8")
    tmp.replace(manifest_path)
    if delete_audio:
        Path(str(removed["audio_path"])).unlink(missing_ok=True)


def mark_verified(sidecar_path: Path, sample_id: str, value: str = "yes") -> None:
    """Çizelgede kontrol durumunu işaretler."""
    if not sidecar_path.exists():
        return
    with sidecar_path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        if row.get("sample_id") == sample_id:
            row["verified"] = value
    tmp = sidecar_path.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SIDECAR_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(sidecar_path)
