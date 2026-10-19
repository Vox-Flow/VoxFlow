# Mimari

```
CLI (cli.py)  ──text──▶ Assistant (services/assistant.py)
   │ listen                 │
   ▼                        ▼
AudioCapture ─▶ SpeechRecognizer ─▶ IntentInterpreter ─▶ DialogueManager ─▶ CommandValidator
(adapters/audio)  (adapters/asr)      (adapters/nlu)        (services)         (services)
                                                                 │ ValidatedCommand
                                                                 ▼
                                   ResponsePresenter ◀── ActionDispatcher ──▶ AllowlistLauncher
                                   (+TTS fallback)        (services)          (adapters/platforms)
                                                                 │
                                                                 ▼
                                                           JsonStore (adapters/storage)
```

## Katmanlar
| Katman | Dosya | Sorumluluk |
|---|---|---|
| Domain | `domain/schemas.py`, `domain/dialogue.py`, `domain/errors.py` | Pydantic sözleşmeler: `Intent`, `IntentResult`, `ValidatedCommand`, `ActionResult`, `Task/Note/HistoryEntry`, hata kodları |
| Ports | `ports/protocols.py` | `AudioCapture`, `SpeechRecognizer`, `IntentInterpreter`, `ActionExecutor`, `SpeechSynthesizer`, `Store` |
| Adapters | `adapters/*` | Kurallı NLU, (ileride) Ollama/Qwen, mock ASR, faster-whisper, sounddevice, JSON depo, allowlist başlatıcı, console/pyttsx3 TTS |
| Services | `services/*` | Tarih çözümleme, doğrulama, diyalog kararı, dispatcher, orkestrasyon, sunum |
| Wiring | `wiring.py`, `config.py` | Config'e göre adaptör seçimi; eksik bağımlılıkta güvenli geri düşüş |

## Güvenlik zinciri (her komut için)
1. NLU çıktısı `IntentResult` şemasına zorlanır; bilinmeyen anahtarlar atılır, parametreler yalnızca skaler.
2. `CommandValidator`: niyet başına `ALLOWED_PARAMETERS` allowlist, zorunlu alan, tarih (ISO), uzunluk, app/site allowlist.
3. `DialogueManager`: tehlikeli niyet (`clear_history`) için açık onay; iptal; eksik parametre sorusu.
4. `ActionDispatcher`: yalnızca sabit `Intent → Python fonksiyonu` tablosu. LLM fonksiyon adı üretemez.
5. `AllowlistLauncher`: `shell=False`, argv config'ten, `which` kontrolü; URL yalnızca config'ten, http/https.

## Durum makinesi (DialogueState)
- `pending_action`: eksik parametre bekleyen niyet (örn. görev başlığı). Sonraki metin ya parametreyi doldurur ya yeni komut olur ya `cancel` ile iptal edilir.
- `pending_confirmation`: `clear_history` için evet/hayır bekler. `affirm` → çalıştır; `deny`/`cancel` → vazgeç.
- Bağlam dışı `evet` → `unknown`.

## Platform desteği
Ortak iş mantığı platformdan bağımsızdır; yalnızca `AllowlistLauncher` komut tablosu ve `default_data_dir` platforma bakar. **Gerçekten test edilen:** Linux (Arch, Python 3.14). Windows/macOS: kod yolu var, test edilmedi (bkz. docs/testing.md).
