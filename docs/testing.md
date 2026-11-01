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
Henüz ölçülmeyen: ASR (WER), uçtan uca işlem başarı oranı, gerçek mikrofon.

## Platform doğrulama tablosu (manuel)
| Özellik | Linux | Windows | macOS |
|---|---|---|---|
| `--text` / `chat` akışları | ✅ Melike, 2026-10-19 | – | – |
| `voxflow info` | ✅ Melike, 2026-10-19 | – | – |
| Uygulama açma (gerçek) | – | – | – |
| Site açma (gerçek tarayıcı) | – | – | – |
| `listen` mikrofon kaydı | – | – | – |
| faster-whisper transkripsiyon | – | – | – |
"–" = henüz denenmedi. CI (GitHub Actions) üç OS'te yalnızca pytest/ruff/CLI duman testini koşar.

### CI'nın yakaladığı platform hatası (2026-10-19)
Windows runner'da `UnicodeEncodeError: 'charmap' codec can't encode character 'ğ'`: Windows konsolu cp1252 kullanıyor. Çözüm: `cli.main` başında stdout/stderr UTF-8'e `reconfigure` edilir; CI'da `PYTHONUTF8=1`. Linux/macOS etkilenmedi.
