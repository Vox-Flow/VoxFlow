# Ekip Görevleri (GitHub Issues'a aktarılabilir)

Roller: **H** Helin (entegrasyon lideri), **İ** İremsu (ses/ASR), **M** Melike (veri/test/CLI). Her iş: sorumlu / destekçi / kabul kriteri / bağımlılık / test / çıktı. Her PR'ı başka bir üye gözden geçirir.

Haftalık rapor ve sunum iskeletleri: `docs/weekly/`.

## Güncel durum (27 Kasım 2026) — kanban: https://github.com/orgs/Vox-Flow/projects/3

**Bitti:** Faz 1 (metin modu), Faz 2 altyapısı (mikrofon, Whisper, kayıt aracı),
Faz 3 (hibrit NLU + ASR hata toleransı + GPU gecikme ölçümü). `v0.1.0` yayımlandı.

**Kritik yol:** veri (İremsu) → eğitim ortamı (Helin) → eğitim koşusu (Helin) →
uyarlama sonrası ölçüm (İremsu) → uçtan uca değerlendirme + rapor (hepimiz).

### Bugün açık işler

| Issue | İş | Sahip | Bağımlılık |
|---|---|---|---|
| #49 (PR) | Common Voice hazırlama hattı — gerçek veriyle koşu | İremsu | — |
| #40 | Günlük: ortam → Common Voice → WER tabanı | İremsu | — |
| #50 | Günlük: #48 düzeltmesi, eğitim ortamı, Windows doğrulaması | Helin | — |
| #35 | Bağımsız NLU test kümesi (nlu_test_v2) | Melike | — |

### Sıradaki işler

| Issue | İş | Sahip | Bağımlılık |
|---|---|---|---|
| #48 | Uydurma tarih doğrulamadan geçiyor (güvenlik) | Helin | — |
| #12 | Windows/macOS platform doğrulaması | Helin | — |
| #4 | WER/CER tabanı (uyarlama öncesi) | İremsu | #49 |
| #8 | **Ana izlek:** Whisper uyarlaması (6 adım, iki sahipli) | İremsu + Helin | #4 |
| #41 | Uçtan uca sesli değerlendirme | Melike | #8 |
| #42 #43 #44 | Rapor bölümleri | Melike / Helin / İremsu | #41 |
| #45 | v1.0 sürüm teslimi ve etiket | Melike | #42–#44 |

**İkinci aşama (ana teslimin parçası değil):** #3 gönüllü ses kaydı, #17 izin formundaki
iki ekip kararı. ADR-010 sonrası bunlar uyarlamayı bloke etmiyor.

**Neden #8 iki sahipli:** veri macOS'ta hazırlanıyor, eğitim Windows + RTX 4050'de koşacak.
Sınır #8'de tablo hâlinde yazılı. Bu yüzden manifestlerdeki `audio_path` depo köküne göre
göreli yazılır — mutlak yol makineler arasında taşınmaz.

## Faz 1 — tamamlanan iskelet
| # | İş | Sorumlu | Durum |
|---|---|---|---|
| 1 | Domain şemaları, port protokolleri | H | ✅ kod + test |
| 2 | Kurallı NLU baseline + tarih çözümleme | H / M | ✅ kod + test |
| 3 | JSON depo (atomik, yedek, bozuk dosya) | M | ✅ kod + test |
| 4 | Allowlist başlatıcı + config | H | ✅ kod + test (mock) |
| 5 | DialogueManager (eksik param, onay, iptal) | H | ✅ kod + test |
| 6 | CLI `--text`/`chat`/`info` | M | ✅ kod + test |

## Faz 2 — ses/ASR
| # | İş | Sorumlu | Destek | Kabul kriteri | Bağımlılık | Test/çıktı |
|---|---|---|---|---|---|---|
| 7 | `SounddeviceCapture` gerçek mikrofon doğrulaması | İ | M | 16 kHz mono, boş/sessiz kayıt hata verir, cihaz yoksa anlaşılır mesaj | #1 | manuel protokol + `docs/testing.md` |
| 8 | faster-whisper model seçimi (tiny/base) ve çevrimdışı yükleme | İ | H | `voxflow info` ASR hazır; uçak modunda transkript | #7, ekip onayı (indirme) | gecikme/bellek ölçümü `experiments/asr/` |
| 9 | 10+ kısa referans kaydı (açık izinli, anonim ID) + ASR manifest | İ | M | manifest şemaya uyar, transkriptler insan kontrollü | #8 | `datasets/manifests/asr_*.jsonl` |
| 10 | WER/CER baseline betiği | İ | M | sentetik manifestte çalışır | #9 | `experiments/asr/eval_wer.py` |

## Faz 3 — NLU
| # | İş | Sorumlu | Destek | Kabul kriteri | Bağımlılık | Test/çıktı |
|---|---|---|---|---|---|---|
| 11 | `OllamaInterpreter` (qwen2.5, JSON mod, sıkı doğrulama, fallback) | H | M | sunucu yokken CLI çökmez; şema dışı çıktı reddedilir | #1 | birim test (HTTP mock) |
| 12 | 50+ Türkçe komut NLU manifesti (farklı söyleyişler, unsupported, boş) | M | H, İ | en az 5 örnek/niyet; konuşmacı/varyant sızıntısı yok | – | `datasets/manifests/nlu_*.jsonl` |
| 13 | Kural vs Qwen karşılaştırma betiği (accuracy, macro-F1, slot EM, geçerli JSON, gecikme) | M | H | aynı test kümesi; rapor tablo | #11, #12 | `experiments/nlu/compare.py`, `experiments/reports/` |

## Faz 4 — eğitim (KARAR: Whisper ana izlek, ADR-008)
| # | İş | Sorumlu | Not |
|---|---|---|---|
| 14a | **ANA İZLEK** Whisper base fine-tune: konfig, manifest doğrulama, smoke test, gerçek eğitim, CT2'ye çevirme, baseline ile aynı testte karşılaştırma | İ (destek M) | iskelet `experiments/asr/` hazır; model indirme ekip onayıyla |
| 14b | (isteğe bağlı yan deney) Qwen2.5 LoRA — yalnızca zaman kalırsa; ana teslimin parçası değil | H | ADR-009 |
| 14c | Ses kayıt izin formu + kayıt protokolü + gönüllü konuşmacı planı (≥8 konuşmacı) | İ (destek M) | `docs/consent_form_tr.md` |
| 15 | Deney kayıt şablonu (config/seed/model/veri sürümü/metrik) | M | her iki izlek için ortak |

## Faz 5 — teslim
| # | İş | Sorumlu |
|---|---|---|
| 16 | 50 komutluk uçtan uca değerlendirme (intent acc ve işlem başarı oranı ayrı) | M |
| 17 | Windows/macOS kontrol listesi ve gerçek test kaydı | H |
| 18 | README/docs güncelleme, izlenebilirlik matrisi | M |
