# Ekip Görevleri (GitHub Issues'a aktarılabilir)

Roller: **H** Helin (entegrasyon lideri), **İ** İremsu (ses/ASR), **M** Melike (veri/test/CLI). Her iş: sorumlu / destekçi / kabul kriteri / bağımlılık / test / çıktı. Her PR'ı başka bir üye gözden geçirir.

## Faz 1 — tamamlanan iskelet (bu oturum)
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

## Faz 4 — eğitim (HOCA YANITI BEKLENİYOR)
| # | İş | Sorumlu | Not |
|---|---|---|---|
| 14a | ASR izleği: Whisper tiny/base fine-tune konfig iskeleti (HF Trainer/PEFT), smoke test sentetik 3 örnek | İ | yalnızca hoca ASR derse |
| 14b | NLU izleği: Qwen2.5 0.5B/1.5B QLoRA konfig iskeleti, smoke test | H | yalnızca hoca NLU derse; 4 GB VRAM sınırı |
| 15 | Deney kayıt şablonu (config/seed/model/veri sürümü/metrik) | M | her iki izlek için ortak |

## Faz 5 — teslim
| # | İş | Sorumlu |
|---|---|---|
| 16 | 50 komutluk uçtan uca değerlendirme (intent acc ve işlem başarı oranı ayrı) | M |
| 17 | Windows/macOS kontrol listesi ve gerçek test kaydı | H |
| 18 | README/docs güncelleme, izlenebilirlik matrisi | M |
