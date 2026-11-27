"""ASR WER/CER değerlendirme iskeleti (Faz 2/4).

Kullanım (model ve ses dosyaları hazır olduğunda):
  .venv/bin/python experiments/asr/eval_wer.py datasets/manifests/asr_test.jsonl --model base

Bu betik `jiwer` ve faster-whisper ister (`pip install 'voxflow[asr]' jiwer`).
Ses dosyaları depoda değildir; manifestteki yerel yollar kullanılır.
Hiçbir model otomatik indirilmez (local_files_only=True).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def normalize_tr(s: str) -> str:
    from voice_assistant.services.text_utils import normalize

    return normalize(s)


def hardware_summary(device: str) -> str:
    details = [f"{platform.system()} {platform.release()}", platform.machine()]
    if hasattr(os, "sysconf"):
        try:
            memory_gib = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
            details.append(f"RAM {memory_gib:.1f} GiB")
        except (OSError, ValueError):
            pass
    if device != "cpu":
        try:
            cmd = ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"]  # noqa: S607
            result = subprocess.run(  # noqa: S603
                cmd, check=True, capture_output=True, text=True, timeout=5
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            details.append("GPU bilgisi alınamadı")
        else:
            gpu = result.stdout.strip().splitlines()
            if gpu:
                details.append("GPU " + "; ".join(gpu))
    return ", ".join(details)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--model", default="base")
    ap.add_argument("--split", default="test")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--compute-type", default="int8")
    ap.add_argument("--report", type=Path)
    ap.add_argument(
        "--initial-prompt",
        default=None,
        help="Whisper initial_prompt; CLI'ın gerçek koşulunu yansıtmak için alan ipucu verilir",
    )
    ap.add_argument(
        "--emit-hyp",
        type=Path,
        default=None,
        help="satır başına {sample_id, transcript, hypothesis} yazar; uçtan uca ölçüm bunu tüketir",
    )
    args = ap.parse_args()

    try:
        import jiwer  # type: ignore[import-not-found]
        import soundfile  # type: ignore[import-not-found]  # noqa: F401  (load_wav kullanır)
    except ImportError:
        print(
            "jiwer ve soundfile gerekli: uv pip install jiwer soundfile 'voxflow[asr]'",
            file=sys.stderr,
        )
        return 2

    from voice_assistant.adapters.asr.faster_whisper_adapter import FasterWhisperRecognizer
    from voice_assistant.adapters.audio.wav_file import load_wav
    from voice_assistant.domain.errors import AudioError

    rec = FasterWhisperRecognizer(
        args.model, args.device, args.compute_type, initial_prompt=args.initial_prompt
    )
    if not rec.is_available():
        print("ASR hazır değil (model indirilmemiş olabilir). Bkz. docs/setup.md", file=sys.stderr)
        return 2

    rows = [
        json.loads(line)
        for line in args.manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = [r for r in rows if r.get("split") == args.split]
    refs, hyps, lat = [], [], []
    emitted: list[dict[str, object]] = []
    for r in rows:
        path = Path(r["audio_path"])
        if not path.exists():
            print(f"atlandı (dosya yok): {path}", file=sys.stderr)
            continue
        try:
            clip = load_wav(path)
        except AudioError as exc:
            print(f"atlandı ({exc}): {path}", file=sys.stderr)
            continue
        t0 = time.perf_counter()
        tr = rec.transcribe(clip)
        lat.append(time.perf_counter() - t0)
        refs.append(normalize_tr(r["transcript"]))
        hyps.append(normalize_tr(tr.text))
        if args.emit_hyp is not None:
            # Ham metin yazılır; normalizasyonu tüketen taraf kendi yapar.
            emitted.append(
                {
                    "sample_id": r["sample_id"],
                    "audio_path": r["audio_path"],
                    "transcript": r["transcript"],
                    "hypothesis": tr.text,
                    "duration_s": r.get("duration_s"),
                }
            )
    if not refs:
        print("Değerlendirilecek örnek yok.", file=sys.stderr)
        return 1
    report = {
        "model": rec.name,
        "n": len(refs),
        "wer": round(jiwer.wer(refs, hyps), 4),
        "cer": round(jiwer.cer(refs, hyps), 4),
        "mean_latency_s": round(sum(lat) / len(lat), 3),
        "hardware": hardware_summary(args.device),
    }
    if args.emit_hyp is not None:
        args.emit_hyp.parent.mkdir(parents=True, exist_ok=True)
        with args.emit_hyp.open("w", encoding="utf-8", newline="\n") as fh:
            for row in emitted:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"Hipotezler: {args.emit_hyp} ({len(emitted)} satır)", file=sys.stderr)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    default_name = f"{time.strftime('%Y-%m-%d')}_asr_baseline_{args.model}.md"
    report_path = args.report or Path("experiments/reports") / default_name
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                f"# ASR baseline — Whisper {args.model}",
                "",
                "| Alan | Değer |",
                "|---|---|",
                f"| Tarih | {time.strftime('%Y-%m-%d')} |",
                "| Koşan | belirtilmedi |",
                "| İzlek | ASR |",
                f"| Model + sürüm | faster-whisper {args.model} ({args.compute_type}) |",
                f"| Veri manifesti + sürüm | {args.manifest} |",
                f"| Split | {args.split} (n = {report['n']}) |",
                f"| Donanım | {report['hardware']} |",
                "",
                "## Metrikler",
                "",
                "| Metrik | Değer |",
                "|---|---|",
                f"| WER | {report['wer']:.4f} |",
                f"| CER | {report['cer']:.4f} |",
                f"| Gecikme (ort.) | {report['mean_latency_s']:.3f} s/örnek |",
                "| Bellek | ölçülmedi |",
                "",
                "## Gözlemler",
                "",
                "- Hata örneklerini değerlendirme sonrası elle ekleyin.",
                "- Sınırlılıklar: gecikme ilk model yükleme süresini içermez; bellek ölçülmedi.",
                "",
                "## Sonuç ve sonraki adım",
                "",
                "Sonuçları ve hata örneklerini gözden geçirin.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Rapor: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
