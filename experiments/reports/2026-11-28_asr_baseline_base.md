# ASR baseline — Whisper base

| Alan | Değer |
|---|---|
| Tarih | 2026-11-28 |
| Koşan | Helin |
| İzlek | ASR |
| Model + sürüm | faster-whisper base (int8) |
| Veri manifesti + sürüm | datasets\manifests\asr_test_real.jsonl |
| Split | test (n = 743) |
| Donanım | Windows 11, AMD64; kartta NVIDIA GeForce RTX 4050 Laptop GPU (6141 MiB) var, ancak **çıkarım CPU'da koştu**: `cublas64_12.dll` bulunamadı, faster-whisper otomatik CPU'ya düştü |

## Metrikler

| Metrik | Değer |
|---|---|
| WER | 0.2586 |
| CER | 0.0677 |
| Gecikme (ort.) | 0.886 s/örnek |
| Bellek | ölçülmedi |

## Gözlemler

- Hata örneklerini değerlendirme sonrası elle ekleyin.
- Sınırlılıklar: gecikme ilk model yükleme süresini içermez; bellek ölçülmedi. **0,886 sn/örnek CPU gecikmesidir**, GPU gecikmesiyle karşılaştırılamaz.
- Beklenen referans: WER 0,2572 / CER 0,0673 (n = 743, Melike, CPU). Bu koşu: 0,2586 / 0,0677; fark 0,0014 (kabul aralığı ±0,005 içinde).
- Veri: FLEURS tr_tr test, 743 örnek, 2,61 sa, `speaker_id: unknown` (konuşmacı-ayrıklık veriden doğrulanamadı); bir örnek 36,84 sn (30 sn Whisper penceresini aşıyor).

## Sonuç ve sonraki adım

Taban referans doğrulandı. Uyarlama sonrası ölçüm aynı test kümesinde (`asr_test_real.jsonl`, 743 örnek) yapılacak. Hata örnekleri henüz eklenmedi.
