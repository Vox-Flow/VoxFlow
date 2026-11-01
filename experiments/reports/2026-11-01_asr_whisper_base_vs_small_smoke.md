# Deney: Whisper base vs small — gerçek mikrofon duman testi (fine-tune öncesi)

| Alan | Değer |
|---|---|
| Tarih | 2026-11-01 |
| Koşan | Melike Nesrin Zaman (konuşmacı: Melike) |
| İzlek | ASR (hazır model, fine-tune yok) |
| Model | faster-whisper `base` ve `small`, int8, **CPU** (cuBLAS 12 yok → otomatik CPU) |
| Ortam | Arch Linux, PipeWire, dahili mikrofon; sessiz oda; tek konuşmacı |
| Veri | 10 komut cümlesi (docs/testing.md listesi); ses kaydedilmedi, yalnızca transkript |
| Betik | `voxflow listen` (uçtan uca), transkript ve gecikme CLI çıktısından |

Bu bir **duman testi**dir: tek konuşmacı, n≈10, WER hesaplanmadı. Amaç fine-tune öncesi davranışı görmek ve ekibe kayıt koşullarını öğretmek.

## Koşu 1 — `base`, prompt yok, mikrofon %27, kayıtlar 3–7 sn, kırpılma %2
| Söylenen | Transkript | Sonuç |
|---|---|---|
| not al süt almayı unutma | "Çek arıyorsunuz, çek ben iyilesin. Not aç. Söyle." | halüsinasyon |
| görev ekle | "Göre bekle." | yanlış |
| not al | "Notar. Notar. Notar." | halüsinasyon |
| görevleri listele | "görevleri listela" | 1 harf hata → NLU unknown (#30) |
| firefox aç | "Fahirfogs" | yanlış |
Önceki GPU koşusunda aynı modelle "görev ekle" (0.41 s) ve "matematik ödevi" (0.52 s) doğruydu → koşullar (kayıt süresi, kırpılma) belirleyici.

## Koşu 2 — `small` + `initial_prompt` (komut kalıpları + allowlist adları), mikrofon %12
| Söylenen | Transkript | Gecikme | Sonuç |
|---|---|---|---|
| görev ekle | "görev ekle" | 1.16 s | ✅ soru soruldu |
| ders programı oluştur (başlık) | "Ders programı oluştur." | 1.21 s | ✅ görev kaydedildi (sondaki nokta başlıkta kaldı → #30) |
| not al, süt almayı unutma, görevleri listele, firefox aç, youtube aç (tek kayıt, 8.7 s) | kelimesi kelimesine doğru | 1.58 s | ASR ✅; NLU tek komut bekler → list_tasks çalıştı |
| geçmişi sil, hayır, vazgeçtim, bilgisayarı kapat, hesap makinesini aç (tek kayıt, 7.0 s) | kelimesi kelimesine doğru | 1.66 s | ASR ✅; NLU → cancel (bekleyen iş yok) |
Kırpılma uyarısı %12 seviyesinde kayboldu (koşu başında %9–10 idi).

## Gözlemler
- `small` + alan sözlüğü ipucu, `base`'in çözemediği yabancı adları ("firefox", "youtube") ve kısa komutları bu koşulda doğru çözdü. Bu, fine-tune olmadan elde edilen iyileştirmedir; raporda "baseline+" satırı olarak ayrı tutulacak.
- `base`'in hataları büyük ölçüde kayıt koşullarına bağlıydı: uzun sessizlik → halüsinasyon, kırpılma → bozulma. Kayıt protokolüne "kısa kayıt, 20–30 cm, kırpılma yok" maddesi eklendi (#17).
- CPU'da `small` gecikmesi 1.2–1.7 s; 7–9 sn kayıtta bile gerçek zamanlıdan hızlı. GPU'da daha düşük beklenir (cuBLAS 12 kurulunca ölçülecek).
- ASR 1-harf hatası ("listela") NLU'da tolere edilmiyor → #30.

## Sınırlılıklar
Tek konuşmacı, tek oturum, ~10 cümle, ses kaydı saklanmadı → WER yok; sayılar kesinlik iddiası değildir. Resmî ölçüm `experiments/asr/eval_wer.py` ile konuşmacı-ayrık test kümesinde yapılacak (#3, #4).

## Karar önerisi
Çıkarım için varsayılan model `small` (config `asr.model_size`). Fine-tune taban modeli (#8) için `base` vs `small` seçimi İremsu'nun WER ölçümünden sonra; 4 GB VRAM'de `small` tam fine-tune sınırda, LoRA gerekebilir (ADR-008).
