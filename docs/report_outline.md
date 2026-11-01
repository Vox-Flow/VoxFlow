# Dönem Sonu Raporu — İskelet ve İzleme

Her bölümde "kaynak" satırı, raporun o kısmının hangi depo dosyasından besleneceğini gösterir. Ölçüm geldikçe ilgili tabloya satır eklenir; rapor yazımı sona bırakılmaz.
Dil: Türkçe. Hedef uzunluk: 20–30 sayfa + ekler. Format kararı (Word/LaTeX) toplantıda.

## 1. Giriş
- Problem: yerel, Türkçe, güvenli sesli bilgisayar asistanı; neden bulut değil.
- Resmî konu ile bağ: "Ses Kayıtlarını Otomatik Yazıya Dönüştürme" → ASR çekirdek, asistan uygulama katmanı.
- Katkılar (madde madde): hexagonal mimari, kurallı+LLM hibrit NLU, kendi ses verisiyle Whisper uyarlaması, üç katmanlı değerlendirme.
- Kaynak: README, `CLAUDE_CODE_SESLI_ASISTAN_MASTER_PROMPT.md` A–B.

## 2. Gereksinimler
- Fonksiyonel (B1–B9) ve güvenlik (D) maddeleri tablo olarak; her satırda uygulama ve test referansı.
- Kaynak: `docs/requirements_traceability.md` (doğrudan tabloya çevrilir).

## 3. İlgili çalışmalar
- ASR: Whisper, faster-whisper/CTranslate2; Türkçe ASR çalışmaları; Common Voice TR.
- NLU: kurallı sistemler vs küçük LLM ile yapılandırılmış çıktı; Türkçe LLM'ler (Qwen, Gemma, yerli modeller) — yalnızca gerçekten okunan kaynaklar; uydurma atıf yok.
- Sorumlu: Helin (NLU), İremsu (ASR). Kaynak listesi: `docs/references.md` (açılacak).

## 4. Mimari ve tasarım
- Katman şeması; port/adaptör; güvenlik zinciri (LLM yalnızca Intent seçer, validator, sabit dispatcher).
- Karar kayıtları: ADR-001…009 özet tablosu (neden/alternatif/karar).
- Diyalog durum makinesi: bekleyen işlem, onay, iptal.
- Kaynak: `docs/architecture.md`, `docs/interfaces.md`, `docs/decisions.md`.

## 5. Veri
- 5.1 NLU test kümesi: nlu_dev_v1 (66; niyet dağılımı tablosu; bağlamlı örnekler; dondurma kuralı).
- 5.2 Ses verisi: izin formu, kayıt protokolü, konuşmacı-ayrık split, toplanan gerçek sayı (**toplanınca yazılır**), kalite bayrakları.
- 5.3 Etik/gizlilik: ham ses saklanmaz, anonim kod, geri çekilme, bulut izni ayrı.
- Kaynak: `docs/dataset_protocol.md`, `docs/consent_form_tr.md`, `docs/recording_sentences_tr.md`, `docs/volunteer_speaker_plan.md`.

## 6. Deneyler ve sonuçlar
Her alt bölümde: kurulum → metrik → tablo → hata analizi → sınırlılık. Sayılar yalnızca `experiments/reports/` dosyalarından.

| Alt bölüm | Durum | Rapor dosyası |
|---|---|---|
| 6.1 Kurallı NLU baseline | ✅ 0.955 / slot 0.924 | `2026-11-01_nlu_rule_based_v1.md` |
| 6.2 Ollama model kıyası (zero/few-shot) | ✅ 4 model, en iyi qwen2.5:3b 0.879 | `2026-11-01_nlu_ollama_model_bench.md` |
| 6.2b Kıyas, diğer donanımlar | ⏳ İremsu, Helin | |
| 6.3 Hibrit NLU (kural + LLM) | ⏳ #27 sonrası | |
| 6.4 Uçtan uca işlem başarı oranı, referans metin | ✅ 0.939, yan etki 0 | `2026-11-01_e2e_reference_text_v1.md` |
| 6.5 ASR baseline (Whisper base, WER/CER, gecikme) | ⏳ #2, #4 | |
| 6.6 Whisper fine-tune vs baseline (aynı test) | ⏳ #8 | |
| 6.7 Uçtan uca, ASR çıktısıyla (baseline vs fine-tuned) | ⏳ ses sonrası | |
| 6.8 Platform doğrulama (Linux/Windows/macOS) | ⏳ `docs/testing.md` tablosu | |

Kural: hedef (%90) ile ölçülen ayrı sütun; n küçükse belirsizlik notu; başarısız/negatif sonuç da yazılır.

## 7. Tartışma
- Niyet doğruluğu ≠ işlem başarısı: nerede ayrıştı.
- Küçük LLM'ler kurala neden yetişmedi; few-shot etkisi; hibritin maliyeti/gecikmesi.
- Whisper uyarlamasının kazancı nerede (alan sözcükleri, konuşmacılar) nerede değil.
- Güvenlik tasarımının gözlenen etkisi (izinsiz yan etki 0).

## 8. Sonuç ve gelecek çalışma
- Yapılanlar / yapılmayanlar (görev silme, wake word, Qwen fine-tune bilinçli dışarıda).
- Gelecek: Qwen LoRA yan deneyi, daha fazla konuşmacı, GUI.

## 9. Ekler
- A: Kurulum ve çevrimdışı çalışma (`docs/setup.md`).
- B: Komut kataloğu ve örnekler (README tablosu).
- C: Test listesi ve CI (`docs/testing.md`).
- D: Ekip görev dağılımı ve zaman çizelgesi (`docs/team_tasks.md`, kanban).
- E: İzin formu (boş).

## Yazım sorumlulukları (öneri, toplantıda onaylanır)
| Bölüm | Yazan | Okuyan |
|---|---|---|
| 1, 2, 5.1, 6.1–6.4, 8, Ekler | Melike | Helin |
| 3 (NLU), 4, 6.3, 7 | Helin | İremsu |
| 3 (ASR), 5.2–5.3, 6.5–6.7 | İremsu | Melike |
