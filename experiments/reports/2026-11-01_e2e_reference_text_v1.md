# Deney: Uçtan uca işlem başarı oranı — referans metin, nlu_dev_v1

| Alan | Değer |
|---|---|
| Tarih | 2026-11-01 |
| Koşan | Melike Nesrin Zaman |
| İzlek | Uçtan uca (NLU → diyalog → işlem); ASR **yok** (referans metin, üst sınır) |
| Bileşenler | RuleBasedInterpreter, DialogueManager, ActionDispatcher, mock launcher, bellek içi depo |
| Veri | datasets/manifests/nlu_dev_v1.jsonl (n = 66) |
| Betik | experiments/e2e/eval_pipeline.py, REFERENCE_TODAY=2026-10-19 |

## Metrikler
| Metrik | Değer |
|---|---|
| intent accuracy | 0.9545 (63/66) |
| **işlem başarı oranı** | **0.9394 (62/66)** |

Niyet başına işlem başarısı: list_tasks 5/6, open_website 4/6, unsupported 9/10; diğer 9 niyet tam.

## Gözlemler
- İşlem başarısı niyet doğruluğundan düşük: iki örnekte niyet doğru (`open_website`) ama site slotu çıkarılamadı, bu yüzden işlem yerine soru soruldu. İki metriği ayrı raporlamanın nedeni bu.
- `instagram'ı aç` niyet olarak yanlış (`open_app`) ama işlem düzeyinde doğru sayıldı: her iki durumda da hiçbir şey açılmadı, kullanıcıya "izinli değil" sorusu soruldu. Yan etki yok.
- 4 hatanın tamamı issue #21'deki kural boşlukları; düzeltildikten sonra aynı kümede yeniden koşulacak.
- Hiçbir örnekte izinsiz yan etki (yanlış görev/not kaydı, yanlış uygulama) gözlenmedi.

## Sınırlılıklar
- ASR'siz; gerçek ses gelince `--text-field hypothesis` ile tekrar koşulur ve bu sonuç üst sınır olarak karşılaştırılır.
- n = 66, tek yazar. Yüzdeler kesinlik iddiası değildir; %90 hedefi burada ASR'siz koşulda aşılmıştır, sesli koşulda henüz ölçülmemiştir.
