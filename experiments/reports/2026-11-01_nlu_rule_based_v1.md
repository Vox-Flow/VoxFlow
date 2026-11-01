# Deney: Kurallı NLU baseline — nlu_dev_v1

| Alan | Değer |
|---|---|
| Tarih | 2026-11-01 |
| Koşan | Melike Nesrin Zaman |
| İzlek | NLU |
| Model + sürüm | RuleBasedInterpreter (develop @ ebd5f1b) |
| Veri manifesti + sürüm | datasets/manifests/nlu_dev_v1.jsonl (ilk sürüm, bu PR) |
| Split | test (n = 66) |
| Config | experiments/nlu/eval_rule_based.py, REFERENCE_TODAY=2026-10-19 |
| Seed | – (belirleyici) |
| Donanım | CPU (Linux, i7 11. nesil) |

## Metrikler
| Metrik | Değer |
|---|---|
| intent accuracy | 0.9545 (63/66) |
| macro-F1 | 0.9636 |
| slot exact match | 0.9242 (61/66) |
| gecikme (ort.) | 0.095 ms |

## Gözlemler (5 hata)
- `yapılacaklar listesini göster` → unknown (gold list_tasks): "listesini" eki kalıpta yok.
- `vikipedi sayfasını aç` → site boş: "sayfasını" eki alias eşleşmesini bozuyor.
- `okul sitesini aç` → site boş: çok kelimeli alias ("okul sitesi") + ek.
- `terminalde ls komutu çalıştır` → open_app (gold unsupported): "terminal" alias'ı serbest komut kalıbından önce yakalanıyor. **Güvenlik açısından önemli:** sonuç yalnızca terminal uygulamasını açar, komut çalıştırmaz; yine de kullanıcıya "desteklenmiyor" denmeli.
- `instagram'ı aç` → open_app (gold open_website): hedef allowlist dışında; "site" sözcüğü geçmediği için uygulama sanılıyor. Her iki durumda da işlem yapılmaz, yalnızca soru farklı.

## Sınırlılıklar
- Tek yazar (ekip içi), sentetik yazılı cümleler; konuşma transkripti değil. ASR hatası içermez.
- 66 örnek küçük; yüzdeler kesinlik iddiası değildir.
- unsupported/unknown toplam 16 örnek; gerçek kullanımda bu oran farklı olabilir.

## Sonuç ve sonraki adım
- Bu küme **dondurulmuş test** kümesidir; kural düzeltmesi ve Qwen karşılaştırması (#5, #7) aynı kümede yapılacak.
- Kural hataları için ayrı issue açıldı (Helin'e); bu PR manifesti değiştirmez, kuralı da değiştirmez.
