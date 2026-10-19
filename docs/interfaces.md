# Arayüz Sözleşmeleri

Tüm adaptörler (gerçek, kurallı, mock) aynı Protocol'ü uygular. Kaynak: `src/voice_assistant/ports/protocols.py`.

| Port | İmza | Notlar |
|---|---|---|
| `AudioCapture` | `start()`, `stop() -> AudioClip`, `close()` | Ses yalnızca bellekte (`PcmClip`). Boş/sessiz kayıt → `AudioError`. |
| `SpeechRecognizer` | `name`, `is_available()`, `transcribe(clip) -> Transcript` | `language="tr"`, `task="transcribe"`. `Transcript.latency_s`, `diagnostics`. |
| `IntentInterpreter` | `name`, `interpret(text, state) -> IntentResult` | Çıktı güvenilmez; validator süzer. |
| `ActionExecutor` | `execute(ValidatedCommand) -> ActionResult` | Yalnızca `ActionDispatcher` tablosu. |
| `SpeechSynthesizer` | `name`, `is_available()`, `speak(text) -> bool` | `False` = sessiz fallback (açıkça bildirilir). |
| `Store` | `add_note`, `add_task`, `list_tasks`, `append_history`, `list_history`, `clear_history` | Not/görev silme-düzenleme **yok**. |

## IntentResult örneği
```json
{"intent": "create_task", "parameters": {"title": "Matematik ödevi", "date": "<YYYY-MM-DD, bugüne göre çözülmüş>"},
 "needs_clarification": false, "clarification_question": null, "confidence": 1.0, "provider": "rule_based"}
```
`date` her zaman ISO; NLU adaptörü göreli ifadeyi (`yarın`) **gerçek bugüne** göre çözer (`services/dates.py`).

## Niyet → izinli parametreler
| intent | izinli | zorunlu | onay |
|---|---|---|---|
| open_app | app | app | – |
| open_website | site | site | – |
| create_note | content | content | – |
| create_task | title, date | title | – |
| list_tasks | date | – | – |
| show_history | limit | – | – |
| clear_history | – | – | **evet** |
| cancel / affirm / deny | – | – | diyalog |
| unknown / unsupported | requested (yalnızca mesaj için) | – | – |

## ActionStatus
`success`, `error` (+`error_code`), `cancelled`, `needs_clarification`, `needs_confirmation`, `unsupported`, `unknown`.

## Hata kodları
`E_CONFIG`, `E_VALIDATION`, `E_STORE`, `E_STORE_CORRUPTED`, `E_ACTION`, `E_APP_NOT_FOUND`, `E_NOT_ALLOWED`, `E_AUDIO`, `E_ASR_UNAVAILABLE`, `E_NLU_UNAVAILABLE`, `E_NOT_CONFIRMED`, `E_UNSUPPORTED`, `E_NO_HANDLER`, `E_UNEXPECTED`.
