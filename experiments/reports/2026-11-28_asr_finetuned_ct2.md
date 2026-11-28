# ASR uyarlama sonrası — whisper-base FLEURS ile uyarlandı (CT2 int8)

| Alan | Değer |
|---|---|
| Tarih | 2026-11-28 |
| Koşan | Helin |
| İzlek | ASR |
| Model + sürüm | openai/whisper-base, FLEURS tr train (617 örnek, 2,00 sa) ile uyarlandı; **en iyi val WER'li kontrol noktası = epoch 1 (`checkpoint-39`)**; CT2 int8 |
| Config | experiments/asr/configs/whisper_base_ft.yaml @ sha256:f9c4d4cbb6af (seed 42; `gradient_checkpointing` için yerel `use_reentrant=False` yaması, commit edilmedi) |
| Veri manifesti + sürüm | datasets\manifests\asr_test_real.jsonl |
| Split | test (n = 743) |
| Donanım | Windows 11, AMD64; kartta RTX 4050 Laptop GPU (6141 MiB) var, **eğitim GPU'da koştu, bu değerlendirme CPU'da** (`cublas64_12.dll` yok, faster-whisper otomatik CPU'ya düştü) |

## Metrikler

| Metrik | Değer |
|---|---|
| WER | **0.3035** (taban: 0.2586, aynı test, aynı CPU/int8 yolu) |
| CER | **0.0894** (taban: 0.0677) |
| Gecikme (ort.) | 0.674 s/örnek (CPU; taban 0.886, aynı koşul değil: ısınma/önbellek farkı olabilir) |
| Bellek | ölçülmedi |

## Gözlemler

- **Uyarlama taban modeli iyileştirmedi, kötüleştirdi:** WER 0,2586 → 0,3035 (+0,0449 mutlak, ≈ %17 göreli), CER 0,0677 → 0,0894. Issue #63'ün baştan uyardığı olası sonuç (alan uyuşmazlığı, küçük veri).
- Eğitim: 5 epoch, 195 adım, 394,6 sn. Val kaybı düzenli düştü (1,07 → 0,53) ama val WER 0,354–0,377 arasında dalgalandı, en iyi epoch 1. `load_best_model_at_end` yüzünden dönüştürülen model epoch 1'inkidir; 5 epoch'un sonu değerlendirilmedi.
- Başlangıç eğitim kaybı 6,38 (önceden eğitilmiş Whisper için yüksek); etiket biçimlendirmesi (ör. başlangıç token'ı) denetlenmedi, sonuç bu yüzden de etkilenmiş olabilir.
- Hata örnekleri henüz eklenmedi (taban ve uyarlanmış çıktılar `--emit-hyp` ile karşılaştırılmadı).
- Sınırlılıklar: tek koşu, tek tohum (42), tek lr (1e-5); konuşmacı-ayrıklık veriden doğrulanamıyor; gecikme ilk model yükleme süresini içermez; bellek ölçülmedi. `run_record.json` yazılmadı (`train_whisper.py:212`, göreli config yolu hatası), koşunun makine-okunur kaydı yok.

## Sonuç ve sonraki adım

Bu ayarla uyarlama **işe yaramadı**; sonuç olduğu gibi raporlanır. Ayrıştırmadan önce denenmesi gerekenler (config'e dokunmadan karar bekliyor, #63): `freeze_encoder: true`, daha düşük öğrenme oranı, etiket biçimlendirmesinin denetimi (başlangıç kaybı 6,38). Taban ile uyarlanmış çıktıların hata karşılaştırması yapılmadı.
