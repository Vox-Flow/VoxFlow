# Test Stratejisi

## Çalıştırma
```bash
uv venv .venv && uv pip install -e '.[dev]'
.venv/bin/python -m pytest            # birim + entegrasyon (model/ses gerekmez)
.venv/bin/ruff check src tests
.venv/bin/mypy src
```

## Katmanlar
- `tests/unit/test_dates.py` — Türkçe tarih ifadeleri (sabit "bugün" ile deterministik).
- `tests/unit/test_rule_based_nlu.py` — niyet/slot çıkarımı, bağlam (bekleyen başlık, onay), prompt-injection metni = düz metin.
- `tests/unit/test_validator.py` — allowlist, bilinmeyen anahtar atma, tarih, onay.
- `tests/unit/test_json_store.py` — atomik yazım, bozuk dosya, yedek, silme API'si yok.
- `tests/unit/test_launcher.py` — sabit argv, eksik ikili, platform komutu yok, geçersiz URL şeması.
- `tests/integration/test_dialogue_flows.py` — **Faz 1 kabul akışları**: görev ekle→ad sor→kaydet; görev ekle→vazgeçtim→kayıt yok; geçmiş sil→onay; app/site mock.
- `tests/integration/test_cli.py` — `--text` modu gerçek `JsonStore` ile; `Popen`/`webbrowser.open` monkeypatch.

## Henüz test edilmeyenler (açıkça)
- `SounddeviceCapture` gerçek mikrofon ile (donanım gerekir) — Faz 2'de manuel protokol.
- `FasterWhisperRecognizer` gerçek model ile (model indirilmedi).
- Ollama adaptörü (Faz 3'te yazılacak).
- Windows/macOS komut yolları (yalnızca kod yolu; `platform_name` parametresi ile birim testte simüle edilebilir).

## Değerlendirme protokolü
Ayrıntı: `docs/evaluation_protocol.md`. Üç ayrı ölçüm: ASR (WER/CER), NLU (intent accuracy, macro-F1, slot EM) ve **işlem başarı oranı** (doğru fonksiyon, doğru parametreyle, mock launcher ile). Metin kümesi: `datasets/manifests/nlu_dev_v1.jsonl` (66, dondurulmuş). Hedef %90 doğru işlem seçimi — ölçülmeden yazılmaz.

## Yapılan ölçümler
| Tarih | Ne | Rapor |
|---|---|---|
| 2026-11-01 | Kurallı NLU, nlu_dev_v1: intent acc 0.955, slot EM 0.924 | `experiments/reports/2026-11-01_nlu_rule_based_v1.md` |
| 2026-11-01 | Ollama model kıyası (qwen2.5 1.5b/3b, gemma3 4b, llama3.2 3b): en iyi qwen2.5:3b few-shot 0.879 | `experiments/reports/2026-11-01_nlu_ollama_model_bench.md` |
| 2026-11-01 | Whisper base vs small gerçek mikrofon duman testi (n≈10, tek konuşmacı): small + initial_prompt tüm komutları doğru yazdı | `experiments/reports/2026-11-01_asr_whisper_base_vs_small_smoke.md` |
| 2026-11-25 | Kural / Qwen 3B / Qwen 1.5B / hibrit karşılaştırması (n=66): kural 1,000 · hibrit 0,985 · 3B 0,803 · 1.5B 0,727 | `experiments/reports/2026-11-25_nlu_provider_comparison.md` |
| 2026-11-25 | Hibrit yönlendirme düzeltmesi sonrası (#37): hibrit **1,000**, LLM çağrısı 4→3, gecikme 473→372 ms | aynı rapor + PR #37 |
Henüz ölçülmeyen: ASR WER (konuşmacı-ayrık küme), uçtan uca sesli işlem başarı oranı.

## Platform doğrulama tablosu (manuel)
| Özellik | Linux | Windows | macOS |
|---|---|---|---|
| `--text` / `chat` akışları | ✅ Melike, 2026-10-19 | – | – |
| ASR hazır değilken `listen` uyarısı | ✅ Melike, 2026-11-01 (E_ASR_UNAVAILABLE, çökme yok) | – | – |
| `voxflow --help` | – | ✅ Helin, 2026-11-27 (Win 11; Türkçe karakterler bozulmadan çıktı) | – |
| `voxflow info` | ✅ Melike, 2026-10-19 | ✅ Helin, 2026-11-27 (Win 11; `platform: windows`, Türkçe çıktı bozulmadı) | – |
| `voxflow devices` | – | ✘ Helin, 2026-11-27: **komut yok** (`invalid choice`); mevcut komutlar chat, listen, info, record, verify | – |
| Uygulama açma (gerçek) | – | – | – |
| Site açma (gerçek tarayıcı) | – | – | – |
| `record` (veri toplama) | – | ✅ Helin, 2026-11-28: sanal kablo sürücüsü kapatılıp varsayılan giriş Realtek olunca 1 kayıt alındı (rms ≈ 0,006) ve manifest yazıldı. 2026-11-27'de sanal kablo varsayılanken **tamamlanamamıştı** (sessizlik, aşağıya bkz.). Not: `--count` yok, `--limit` ve `--speaker spk_NN`, `--split` gerekir | – |
| `listen` mikrofon kaydı | ✅ Melike, 2026-11-01 (dahili mikrofon, PipeWire; loopback ile sentetik sinyal de doğrulandı) | ✅ Helin, 2026-11-28: Realtek, Enter-Enter-çık akışı, 5,9 sn kayıt, çökme yok, çıkış kodu 0, Türkçe çıktı bozulmadı. 2026-11-27'de sanal kablo yüzünden doğrulanamamıştı | – |
| faster-whisper transkripsiyon | ✅ Melike, 2026-11-01 (small+prompt, CPU; rapor: `experiments/reports/2026-11-01_asr_whisper_base_vs_small_smoke.md`) | ✅ Helin, 2026-11-28: `listen` ile gerçek mikrofon, `base`, CPU, 0,79 sn; "Saat kaç" doğru tanındı ama sonuna uydurma "Saat altuz." eklendi. **Tek deneme, duman testi; ölçüm değil.** Toplu WER: `experiments/reports/2026-11-28_asr_baseline_base.md` (FLEURS, CPU) | – |
"–" = henüz denenmedi. CI (GitHub Actions) üç OS'te yalnızca pytest/ruff/CLI duman testini koşar.

### Windows denemesi (2026-11-27, Helin)
Ortam: Windows 11 Pro, Python 3.12, sounddevice 0.5.6, MME/WASAPI/WDM-KS sürücüleri.
| Kontrol | Sonuç |
|---|---|
| Mikrofon gizlilik izni (kayıt defteri) | ✅ `Allow` |
| `sounddevice` cihaz listesi | ✅ 29 giriş/çıkış aygıtı listelendi |
| Realtek mikrofon (MME), 16 kHz mono, 2 sn, bellekte | ✅ rms 0,006–0,008 (oda sesi) |
| Realtek mikrofon (WASAPI, 16 kHz) | ✘ `PortAudioError: Invalid sample rate [-9997]` |
| Varsayılan giriş (`Line 1 (Virtual Audio Cable)`) | ✘ **sessizlik**: rms 0,00001, tepe 0,0000 |
| Microsoft Sound Mapper (Windows varsayılanını izler) | ✘ aynı sessizlik |
| Türkçe karakterli çıktı (`--help`, `info`) | ✅ `PYTHONUTF8` ayarlanmadan bozulma yok |

**Bulgu 1 — cihaz seçilemiyor:** `SounddeviceCapture` `InputStream`'i cihaz vermeden açar, yani Windows'un varsayılan giriş cihazını kullanır. Bu makinede varsayılan sanal bir ses kablosu olduğu için `record` ve `listen` **sessizlik kaydeder**; hata vermez, kullanıcıya "çalıştı" gibi görünür. Varsayılanı Realtek'e çevirme denemesi (Ayarlar ve `mmsys.cpl`) bu makinede uygulanmadı; neden belirlenemedi (sanal kablo yazılımı varsayılanı geri almış olabilir).
**Bulgu 1 çözümü (2026-11-28, yalnızca bu makine):** "Virtual Audio Cable" sürücüsü Aygıt Yöneticisi'nden devre dışı bırakıldı (yönetici yetkisiyle); varsayılan giriş Realtek'e döndü ve `record`/`listen` çalıştı. Bu bir ortam çözümü; uygulama hâlâ cihaz seçmiyor, varsayılan giriş sanal kablo olan herkes aynı sessizliği alır.
**Bulgu 2 — sessizlik uyarısı:** `listen` yolunda RMS<1e-4 uyarısı Linux'ta birim testle doğrulanmıştı. Windows'ta sessiz girişle gerçek akışta **görülmedi** (2026-11-27'deki koşuda uyarı çıktığına dair kayıt yok; 2026-11-28'de giriş sessiz olmadığı için tetiklenmedi, yeniden denenmedi).
**Bulgu 3 — komut/dokümantasyon farkı:** `voxflow devices` yok, `record --count` yok. Cihaz listesi için şimdilik `python -c "import sounddevice as sd; print(sd.query_devices())"`.
**Bulgu 4 — WASAPI:** 16 kHz paylaşımlı kipte reddediliyor; uygulama WASAPI seçerse yeniden örnekleme gerekir (şu an MME varsayılan).
`voxflow devices` (PR #64) bu tabloda **henüz doğrulanmış sayılmaz**: `--device` indeksle denendi ve çalışıyor, ad parçasıyla seçim Windows'ta aynı mikrofon her host API'de ayrı listelendiği için çoklu eşleşme veriyor; ayrıntı #64 yorumunda. Merge olunca satırı güncelleyin.
Önerilen ayrı issue'lar (düzeltilmedi): (a) `--device` seçeneği ve cihaz listesi komutu, (b) sessiz kayıt tespiti ve uyarısı, (c) WASAPI örnekleme hızı.

### CI'nın yakaladığı platform hatası (2026-10-19)
Windows runner'da `UnicodeEncodeError: 'charmap' codec can't encode character 'ğ'`: Windows konsolu cp1252 kullanıyor. Çözüm: `cli.main` başında stdout/stderr UTF-8'e `reconfigure` edilir; CI'da `PYTHONUTF8=1`. Linux/macOS etkilenmedi.

### Linux mikrofon denemesi (2026-11-01, Melike)
Ortam: Arch Linux, PipeWire, dahili mikrofon (HDA Intel ALC256), Python 3.14, sounddevice 0.5.6.
| Kontrol | Sonuç |
|---|---|
| 2 sn gerçek kayıt, 16 kHz mono float32 | ✅ |
| ALSA loopback ile 440 Hz sentetik sinyal | ✅ rms 0.19, mono, 2.36 sn |
| stop-before-start / çift start / close | ✅ anlaşılır AudioError |
| CLI `listen` Enter-Enter-çık akışı (mock ASR) | ✅ |
| ASR yokken `listen` | ✅ E_ASR_UNAVAILABLE mesajı, metin moduna yönlendirme |
| **Bulgu 1:** Enter'a hemen basınca 0.01 sn'lik kayıt hata vermeden ASR'a gidiyordu | düzeltildi: `MIN_SECONDS=0.3`, "Kayıt çok kısa" hatası |
| **Bulgu 2:** ilk gerçek kayıtta tepe değer 1.05 (kırpılma) | eklendi: tam ölçekli örnek oranı >%0.1 ise uyarı; kullanıcıya kazanç düşürme önerisi |
Sessiz kayıt yolu (RMS<1e-4) gerçek mikrofonla tetiklenemedi (oda gürültüsü yeterli); birim testle doğrulandı.
| **Bulgu 3:** fish kabuğunda `uv run voxflow listen` → 8.8 sn kayıt sonrası `RuntimeError: libcublas.so.12 not found` ile çökme (GPU kütüphanesi yok) | düzeltildi: yüklemede ısınma koşusu; GPU hatasında CPU'ya düşme; transkripsiyon hataları `E_ASR_UNAVAILABLE` olarak sarılır, traceback yok |
| **Bulgu 4:** `uv run` extras'sız çalıştırılınca ses/ASR paketlerini kaldırıyor | docs/setup.md'ye uyarı; komut `uv run --extra audio --extra asr voxflow listen` |
