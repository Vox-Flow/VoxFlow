# experiments/
- `nlu/eval_rule_based.py` — kurallı NLU baseline metrikleri (intent accuracy, macro-F1, slot EM, gecikme). İleride `--provider ollama|finetuned` eklenecek.
- `asr/eval_wer.py` — WER/CER iskeleti; model + ses dosyaları hazır olduğunda çalışır. Model indirmez.
- `reports/` — her çalışma: tarih, config, seed, model/veri sürümü, metrik. Boş; **hiçbir ölçüm henüz yapılmadı**.

Fine-tuning izleği (ASR mi NLU mu) hocanın yanıtını bekliyor; bkz. `docs/decisions.md` ADR-007.
