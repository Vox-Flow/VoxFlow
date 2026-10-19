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

## Değerlendirme protokolü (Faz 5 için taslak)
- ≥50 gerçek komut; `datasets/manifests/nlu_*.jsonl`. Intent accuracy, slot exact-match ve **işlem başarı oranı ayrı** raporlanır.
- Hedef %90 doğru işlem seçimi — ölçülmeden yazılmaz.

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
