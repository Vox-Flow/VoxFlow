# Gereksinim → Özellik → Test İzlenebilirliği

| Gereksinim (B/D maddesi) | Uygulama | Test |
|---|---|---|
| B2 yalnızca izinli uygulamalar | `AllowlistLauncher`, `CommandValidator.allowed_apps` | `test_launcher.py`, `test_validator.py::test_app_not_in_allowlist`, `test_dialogue_flows.py::test_open_unknown_app_does_nothing` |
| B3 not/görev ekle, listele; silme/düzenleme yok | `JsonStore` (yalnızca add/list), `UNSUPPORTED_PATTERNS` | `test_json_store.py::test_store_has_no_delete_for_tasks_or_notes`, `test_unsupported_lists_alternatives` |
| B4 internetsiz temel işlev | kurallı NLU, JSON depo, mock ASR varsayılan | tüm testler ağ olmadan koşar |
| B5 Enter ile başlat/bitir | `cli.run_listen` | manuel (Faz 2) |
| B6 eksik → sor; desteklenmeyen → söyle | `DialogueManager`, `Intent.UNSUPPORTED` | `test_task_with_clarification_saves`, `test_unsupported_lists_alternatives` |
| B7 geçmiş metin+sonuç+zaman; ham ses yok | `HistoryEntry`, `Assistant._record` | `test_history_clear_returns_count`, `test_show_history` |
| B8 yalnızca tanımlı siteler | `SiteSpec`, `_validate_url` | `test_open_site_not_allowed`, `test_invalid_scheme_in_config_rejected` |
| B9 iptal yalnızca bekleyen işlem | `DialogueManager` cancel dalı | `test_task_then_cancel_saves_nothing`, `test_cancel_without_pending` |
| C onay gerektiren geçmiş silme | `CONFIRMATION_REQUIRED`, `PendingConfirmation` | `test_clear_history_requires_confirmation` |
| C tarih tahmin etme | `find_date` → None, validator hata | `test_find_date_none`, `test_bad_date_is_error_not_guess` |
| C webbrowser "yüklendi" deme | `_open_site` mesajı | `test_open_app_and_site` |
| D shell yok, LLM komutu yok | `Popen(list, shell=False)`, dispatcher tablosu | `test_open_app_uses_fixed_argv`, `test_unknown_keys_are_dropped` |
| D prompt injection = düz metin | NLU metni yalnızca slot | `test_prompt_injection_text_is_just_text` |
| D atomik JSON, bozuk dosya | `JsonStore._write/_read` | `test_corrupted_file_raises`, `test_no_temp_files_left`, `test_backup_created_on_rewrite` |
| Ek: ≥50 komutla değerlendirme | `datasets/manifests/nlu_dev_v1.jsonl` (66), `experiments/nlu/eval_rule_based.py`, `docs/evaluation_protocol.md` | `test_asr_manifest_validation.py`; ölçüm raporları `experiments/reports/` |
| F: fine-tune hedefi ASR; NLU eğitilmez | ADR-008, ADR-009; `experiments/asr/train_whisper.py`; hibrit NLU planı | `train_whisper.py --dry-run`; `bench_ollama_quick.py` |
| G: ASR/NLU manifest ayrımı, konuşmacı sızıntısı | `docs/dataset_protocol.md`, `experiments/asr/validate_manifest.py` | `test_speaker_leak_detected`, `test_missing_consent_is_error` |
| G: izinli, anonim ses toplama | `docs/consent_form_tr.md` | manuel (ekip onayı, #17) |
