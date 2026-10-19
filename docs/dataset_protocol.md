# Veri Seti Protokolü

İki ayrı manifest; aynı kayıt her ikisinde yer alabilir ama zorunlu değildir.

## ASR manifesti (`datasets/manifests/asr_*.jsonl`, satır başına JSON)
`sample_id, audio_path, transcript, speaker_id, language, duration_s, split, source, consent_or_license, quality_flags`
- `audio_path` depoda **yok** (gitignore); yalnızca yerel yol. `speaker_id` anonim (`spk_01`).
- `transcript` insan tarafından kontrol edilmiş; ASR çıktısı otomatik etiket **değildir**.
- `consent_or_license`: `team_consent_v1` (ekip içi açık izin formu) ya da dış veri lisansı (örn. Common Voice — lisans/erişim koşulları kullanılmadan önce doğrulanacak).
- `quality_flags`: `noise`, `clipping`, `silence`, `truncated`, `ok`.

## NLU manifesti (`datasets/manifests/nlu_*.jsonl`)
`sample_id, utterance, intent, slots, dialogue_context, split, source`
- `intent` ∈ katalog (`domain/schemas.py::Intent`); `slots` yalnızca izinli parametreler. Göreli tarihler `slots.date_text` olarak **metin** tutulur; ISO'ya değerlendirme anında, sabit bir referans günle çevrilir.
- `dialogue_context`: `null` | `{"pending": "create_task.title"}` | `{"pending_confirmation": "clear_history"}`.
- `source`: `synthetic`, `team_written`, `team_spoken_transcribed`.

## Bölme kuralları
- ASR: konuşmacı bazlı split (aynı `speaker_id` iki split'te olmaz).
- NLU: aynı cümlenin birebir/çok yakın varyantları aynı split'te kalır (ezber avantajı yok).
- Test kümesi dondurulur; baseline ve fine-tuned model **aynı** test kümesinde değerlendirilir.

## Toplama hedefleri (öneri, ölçülmüş sayı değil)
- NLU: ≥50 komut değerlendirme, ≥5 örnek/niyet, ≥10 unsupported/unknown.
- ASR: ekip içi 3 konuşmacı × 20 kısa komut başlangıç; 16 kHz mono WAV, sessiz oda + 1 gürültülü set.
- Senaryolar: farklı söyleyiş, sessizlik, mikrofon yok, gürültü, tanımsız istek.

## Gizlilik
Gerçek konuşma geçmişi (`history.json`) eğitim verisine otomatik kopyalanmaz. Yalnızca açık izinli, anonimleştirilmiş kayıtlar manifestlere girer.
