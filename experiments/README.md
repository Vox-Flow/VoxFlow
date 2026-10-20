# experiments/
- `nlu/eval_rule_based.py` — kurallı NLU baseline metrikleri (intent accuracy, macro-F1, slot EM, gecikme). İleride `--provider ollama|finetuned` eklenecek.
- `asr/eval_wer.py` — WER/CER iskeleti; model + ses dosyaları hazır olduğunda çalışır. Model indirmez.
- `reports/` — her çalışma: tarih, config, seed, model/veri sürümü, metrik. Boş; **hiçbir ölçüm henüz yapılmadı**.

- `asr/validate_manifest.py` — manifest şema/split/izin/konuşmacı-sızıntısı denetimi (model gerektirmez; birim testi var).
- `asr/train_whisper.py` — Whisper base fine-tune (ADR-008). `--dry-run` model yüklemez. Ağırlık yerelde yoksa indirmez, açık hata verir.
- `asr/configs/whisper_base_ft.yaml` — başlangıç hiperparametreleri; her çalışmada sha256'sı rapora yazılır.

Karar (2026-10-20): ana fine-tune izleği **Whisper**; Qwen eğitilmez (ADR-008/009).
