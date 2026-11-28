"""Uyarlanmış Whisper (HF) modelini CTranslate2'ye çevirir (faster-whisper için).

Kullanım:
  python experiments/asr/convert_to_ct2.py \\
      --model experiments/asr/runs/latest/final \\
      --output models/whisper-base-tr-commands-ct2 --quantization int8

Eşdeğer CLI: ct2-transformers-converter --model <hf-çıktı> --quantization int8 --output_dir <çıktı>
Ağdan hiçbir şey indirilmez (yerel dizinden dönüştürülür). Çıktı git dışıdır (`models/`).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# faster-whisper, model dizininde bunları bekler (dönüştürücü kopyalamazsa eksik kalır).
COPY_FILES = ["tokenizer.json", "preprocessor_config.json"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument(
        "--model", type=Path, required=True, help="HF model dizini (train çıktısı final/)"
    )
    ap.add_argument("--output", type=Path, required=True, help="CT2 çıktı dizini")
    ap.add_argument(
        "--quantization", default="int8", choices=["int8", "int8_float16", "float16", "float32"]
    )
    ap.add_argument("--force", action="store_true", help="çıktı dizini varsa üzerine yaz")
    args = ap.parse_args()

    if not args.model.is_dir():
        print(f"HATA: {args.model} yok.", file=sys.stderr)
        return 2
    if args.output.exists() and not args.force:
        print(f"HATA: {args.output} zaten var; üzerine yazmak için --force verin.", file=sys.stderr)
        return 2

    try:
        from ctranslate2.converters import TransformersConverter
    except ImportError:
        print("ctranslate2 gerekli: uv sync --extra asr --extra train", file=sys.stderr)
        return 2

    copy_files = [f for f in COPY_FILES if (args.model / f).is_file()]
    converter = TransformersConverter(
        str(args.model), copy_files=copy_files, low_cpu_mem_usage=True
    )
    out = converter.convert(str(args.output), quantization=args.quantization, force=args.force)
    print(f"Dönüştürüldü: {out}  (quantization={args.quantization}, kopyalanan={copy_files})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
