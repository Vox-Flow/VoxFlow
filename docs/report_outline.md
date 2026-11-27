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
- 5.1 NLU kümeleri: `nlu_dev_v1` (66, geliştirme) ve `nlu_test_v2` (36, **tutulmuş**;
  12 niyetin hepsi temsil ediliyor, dev ile tek cümle örtüşmüyor). Dondurma kuralı:
  tutulmuş kümenin hatalarına bakarak kural yazmak onu geliştirme kümesine çevirir.
- 5.2 Ses verisi: **FLEURS Türkçe** (CC-BY-4.0, ADR-011) — train 617 örnek/2,00 sa,
  val 338/1,12 sa, test 743/2,61 sa. Common Voice'tan neden vazgeçildiği (Mozilla
  Ekim 2025'te Hugging Face'ten kaldırdı). **Dürüstlük notu:** FLEURS konuşmacı kimliği
  yayımlamıyor; konuşmacı-ayrıklık veriden doğrulanamıyor, resmî bölmelere güveniliyor.
  Doğrulanabilen şey cümle ayrıklığıdır: train∩test = 0, train∩dev = 0, dev∩test = 0.
  Alan uyuşmazlığı: FLEURS haber cümleleri (ort. 12,6 sn), bizim alanımız 1–3 sn komutlar.
  Kendi gönüllü kayıtlarımız (izin formu, kayıt protokolü) ikinci aşama.
- 5.3 Etik/gizlilik: ham ses saklanmaz, anonim kod, geri çekilme, bulut izni ayrı.
- Kaynak: `docs/dataset_protocol.md`, `docs/consent_form_tr.md`, `docs/recording_sentences_tr.md`, `docs/volunteer_speaker_plan.md`.

## 6. Deneyler ve sonuçlar
Her alt bölümde: kurulum → metrik → tablo → hata analizi → sınırlılık. Sayılar yalnızca `experiments/reports/` dosyalarından.

**Hangi küme hangi amaçla:** `nlu_dev_v1` (n=66) bir **geliştirme** kümesidir — hataları
kuralları düzeltmek için kullanıldı, oradaki sonuç genelleme başarımı değildir.
Rapora girecek NLU sayıları **tutulmuş** `nlu_test_v2` (n=36) kümesinden gelir.

| Alt bölüm | Durum | Sayı | Rapor dosyası |
|---|---|---|---|
| 6.1 Kurallı NLU, geliştirme kümesi | ✅ | niyet 1,000 · slot 1,000 (n=66) | `2026-11-01_nlu_rule_based_v1.md` |
| 6.1b **Kurallı NLU, tutulmuş küme** | ✅ | **niyet 0,722 · makro-F1 0,720 · slot 0,694** (n=36) | `2026-11-27_nlu_holdout_v2.md` |
| 6.2 Ollama model kıyası (zero/few-shot) | ✅ | en iyi qwen2.5:3b 0,879 | `2026-11-01_nlu_ollama_model_bench.md` |
| 6.2b Kıyas, diğer donanımlar | ✅ | GPU gecikme 6434 → 381 ms | `2026-11-25_nlu_qwen25_3b_gpu.md` |
| 6.3 Hibrit NLU (kural + LLM) | ✅ | 0,985 → düzeltme sonrası 1,000 (dev) | `2026-11-25_nlu_provider_comparison.md` |
| 6.4 Uçtan uca, referans metin | ✅ | dev 1,000 · **tutulmuş 0,694** | ⚠ eski `2026-11-01_e2e_reference_text_v1.md` içindeki **0,939 bayattır** (#21/#37/#38 öncesi kod) |
| 6.5 **ASR taban (FLEURS test, n=743)** | ✅ | **base WER 0,2572 · CER 0,0673** · small WER 0,1350 · CER 0,0339 | `2026-11-27_asr_baseline_fleurs.md` |
| 6.6 Whisper uyarlaması vs taban (aynı test) | ⏳ | — | #63, Helin |
| 6.7 Uçtan uca, ASR çıktısıyla | ⏳ | — | sesli kayıt sonrası (#41) |
| 6.8 Platform doğrulama (Linux/Windows/macOS) | ◐ | Windows kısmen ✘ | `docs/testing.md` |

Kural: hedef (%90) ile ölçülen ayrı sütun; n küçükse belirsizlik notu; başarısız/negatif
sonuç da yazılır. **Dev kümesindeki 1,000'ler tek başına raporlanmaz**, yanında mutlaka
tutulmuş küme sayısı verilir.

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
