"""Whisper fine-tune betiği (ADR-008). Model indirmez; ağırlıklar yerelde yoksa açık hata verir.

Aşamalar:
  --dry-run : config + manifestleri doğrular, hiçbir model yüklemez (CI/smoke test için).
  (normal)  : HF transformers Seq2SeqTrainer ile eğitim. Gerekli: uv sync --extra train
              ve openai/whisper-base ağırlıklarının önceden indirilmiş olması
              (HF cache).

Kullanım:
  uv run python experiments/asr/train_whisper.py experiments/asr/configs/whisper_base_ft.yaml --dry-run
  uv run python experiments/asr/train_whisper.py experiments/asr/configs/whisper_base_ft.yaml --output runs/v0

Her çalışma sonunda experiments/reports/TEMPLATE.md doldurulur (config hash, seed, metrik).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_manifest import validate  # noqa: E402


def load_config(path: Path) -> dict:  # type: ignore[type-arg]
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        # PyYAML yoksa çok basit bir okuyucu yerine açık hata: train extras kurulmalı.
        raise SystemExit(
            "PyYAML gerekli: uv sync --extra train  (veya: uv pip install pyyaml)"
        ) from None
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    for key in ("base_model", "language", "task", "data", "training"):
        if key not in cfg:
            raise SystemExit(f"config eksik alan: {key}")
    if cfg["task"] != "transcribe":
        raise SystemExit("task yalnızca 'transcribe' olabilir (çeviri yok).")
    return cfg


def config_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def dry_run(cfg: dict, cfg_path: Path) -> int:  # type: ignore[type-arg]
    d = cfg["data"]
    paths = [ROOT / d[k] for k in ("train_manifest", "val_manifest", "test_manifest")]
    missing = [p for p in paths if not p.exists()]
    print(f"config: {cfg_path.name} sha256:{config_hash(cfg_path)}")
    print(f"model : {cfg['base_model']}  lang={cfg['language']} task={cfg['task']}")
    if missing:
        print("manifest(ler) yok (gerçek veri henüz toplanmadı):")
        for p in missing:
            print("  -", p.relative_to(ROOT))
        print("DRY-RUN: config geçerli; veri bekleniyor.")
        return 0
    rep = validate(paths, check_files=True)
    print(f"örnek: {rep.n}, süre: {rep.total_duration_s / 60:.1f} dk, hata: {len(rep.errors)}")
    for e in rep.errors[:20]:
        print("HATA:", e)
    return 0 if rep.ok else 1


def train(cfg: dict, cfg_path: Path, output: Path) -> int:  # type: ignore[type-arg]
    try:
        import torch
        from datasets import Audio, load_dataset
        from transformers import (
            Seq2SeqTrainer,
            Seq2SeqTrainingArguments,
            WhisperForConditionalGeneration,
            WhisperProcessor,
        )
    except ImportError as exc:
        raise SystemExit(f"Eğitim bağımlılıkları eksik ({exc}). uv sync --extra train") from None
    try:
        import evaluate
    except ImportError:
        raise SystemExit("'evaluate' ve 'jiwer' gerekli: uv pip install evaluate jiwer") from None

    d, t = cfg["data"], cfg["training"]
    torch.manual_seed(int(t.get("seed", 42)))

    # Ağırlıklar yerelde olmalı; ağdan indirme yapılmaz.
    try:
        processor = WhisperProcessor.from_pretrained(
            cfg["base_model"], language="turkish", task="transcribe", local_files_only=True
        )
        model = WhisperForConditionalGeneration.from_pretrained(
            cfg["base_model"], local_files_only=True
        )
    except OSError:
        raise SystemExit(
            f"{cfg['base_model']} yerelde yok. Ekip onayıyla bir kez indirin:\n"
            f'  uv run python -c "from transformers import WhisperForConditionalGeneration as M, WhisperProcessor as P; '
            f"M.from_pretrained('{cfg['base_model']}'); P.from_pretrained('{cfg['base_model']}')\""
        ) from None
    model.generation_config.language = "turkish"
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None
    if t.get("gradient_checkpointing"):
        model.gradient_checkpointing_enable()
        model.config.use_cache = False
    if t.get("freeze_encoder"):
        model.freeze_encoder()

    if cfg.get("lora", {}).get("enabled"):
        from peft import LoraConfig, get_peft_model

        lc = cfg["lora"]
        model = get_peft_model(
            model,
            LoraConfig(
                r=lc["r"],
                lora_alpha=lc["alpha"],
                lora_dropout=lc["dropout"],
                target_modules=lc["target_modules"],
            ),
        )

    files = {k: str(ROOT / d[f"{k}_manifest"]) for k in ("train", "val")}
    ds = load_dataset("json", data_files=files)
    ds = ds.cast_column("audio_path", Audio(sampling_rate=d["sample_rate"]))

    from voice_assistant.services.text_utils import normalize

    def prep(batch):  # type: ignore[no-untyped-def]
        audio = batch["audio_path"]
        batch["input_features"] = processor.feature_extractor(
            audio["array"], sampling_rate=audio["sampling_rate"]
        ).input_features[0]
        batch["labels"] = processor.tokenizer(normalize(batch["transcript"])).input_ids
        return batch

    ds = ds.map(prep, remove_columns=ds["train"].column_names)

    class Collator:
        def __call__(self, feats):  # type: ignore[no-untyped-def]
            inp = processor.feature_extractor.pad(
                [{"input_features": f["input_features"]} for f in feats], return_tensors="pt"
            )
            lab = processor.tokenizer.pad(
                [{"input_ids": f["labels"]} for f in feats], return_tensors="pt"
            )
            labels = lab["input_ids"].masked_fill(lab.attention_mask.ne(1), -100)
            if (labels[:, 0] == processor.tokenizer.bos_token_id).all():
                labels = labels[:, 1:]
            inp["labels"] = labels
            return inp

    wer_metric = evaluate.load("wer")
    cer_metric = evaluate.load("cer")

    def compute_metrics(pred):  # type: ignore[no-untyped-def]
        ids = pred.label_ids
        ids[ids == -100] = processor.tokenizer.pad_token_id
        hyp = [
            normalize(s) for s in processor.batch_decode(pred.predictions, skip_special_tokens=True)
        ]
        ref = [normalize(s) for s in processor.batch_decode(ids, skip_special_tokens=True)]
        return {
            "wer": wer_metric.compute(predictions=hyp, references=ref),
            "cer": cer_metric.compute(predictions=hyp, references=ref),
        }

    args = Seq2SeqTrainingArguments(
        output_dir=str(output),
        run_name=cfg.get("run_name"),
        seed=int(t.get("seed", 42)),
        num_train_epochs=t["epochs"],
        per_device_train_batch_size=t["per_device_train_batch_size"],
        per_device_eval_batch_size=t.get("per_device_eval_batch_size", 8),
        gradient_accumulation_steps=t.get("gradient_accumulation_steps", 1),
        learning_rate=float(t["learning_rate"]),
        warmup_steps=t.get("warmup_steps", 0),
        weight_decay=t.get("weight_decay", 0.0),
        fp16=bool(t.get("fp16", False)) and torch.cuda.is_available(),
        eval_strategy=t.get("eval_strategy", "epoch"),
        save_strategy=t.get("save_strategy", "epoch"),
        predict_with_generate=True,
        generation_max_length=128,
        load_best_model_at_end=True,
        metric_for_best_model=t.get("metric_for_best_model", "wer"),
        greater_is_better=bool(t.get("greater_is_better", False)),
        logging_steps=10,
        report_to=[],  # telemetri yok
        save_total_limit=2,
    )
    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=ds["train"],
        eval_dataset=ds["val"],
        data_collator=Collator(),
        compute_metrics=compute_metrics,
        processing_class=processor.feature_extractor,
    )
    trainer.train()
    trainer.save_model(str(output / "final"))
    processor.save_pretrained(str(output / "final"))
    metrics = trainer.evaluate()
    (output / "run_record.json").write_text(
        json.dumps(
            {
                "config": str(cfg_path.relative_to(ROOT)),
                "config_sha256": config_hash(cfg_path),
                "base_model": cfg["base_model"],
                "seed": t.get("seed", 42),
                "val_metrics": metrics,
                "note": "Test kümesi ayrı değerlendirilir: experiments/asr/eval_wer.py "
                "(baseline ile aynı test).",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(metrics, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--output", type=Path, default=ROOT / "experiments/asr/runs/latest")
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.dry_run:
        return dry_run(cfg, a.config)
    a.output.mkdir(parents=True, exist_ok=True)
    return train(cfg, a.config, a.output)


if __name__ == "__main__":
    sys.exit(main())
