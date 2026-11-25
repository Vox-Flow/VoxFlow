# CLAUDE.md — VoxFlow için çalışma kuralları

Bu depo 61. Grup dönem projesidir (Türkçe yerel sesli asistan). Ana mühendislik talimatı:
`CLAUDE_CODE_SESLI_ASISTAN_MASTER_PROMPT.md`. Oradaki B (ürün kararları) ve D (güvenlik) maddeleri
**değiştirilemez**; çelişen istek gelirse önce bunu söyle.

## Çalışmaya başlamadan
- `docs/decisions.md` (ADR) ve `docs/team_tasks.md` oku; yapılmış işi yeniden yazma.
- Fine-tune kararı verildi (ADR-008/009): ana izlek Whisper; Qwen eğitilmez. Yine de model/dataset indirme ve eğitim başlatma **ekip onayı** ister.
- Kişisel veri (`config/*.json`, `history.json`, ses dosyaları) asla commit edilmez.

## Git akışı
- `main`: korumalı, yalnızca `develop`'tan PR ile (faz teslimi + tag). Doğrudan push **yok**.
- `develop`: korumalı, yalnızca `feat/*`, `fix/*`, `docs/*`, `test/*`, `exp/*` dallarından PR ile.
- Commit: Conventional Commits, Türkçe açıklama serbest: `feat(nlu): Ollama adaptörü eklendi`.
- Commit/push yalnızca kullanıcı isterse. Geçmiş yeniden yazılmaz (`--force`, `rebase` paylaşılan dalda yok).

## Kod kuralları
- Python ≥ 3.11, `src/voice_assistant/` hexagonal yapı: `domain → ports → adapters/services`.
- Yeni davranış = yeni test. Çalıştırmadan "geçti" deme:
  `uv run pytest`, `uv run ruff check src tests experiments`, `uv run ruff format --check src tests experiments`.
- LLM/kural çıktısı güvenilmez girdidir: yalnızca `Intent` seçer, `CommandValidator` süzer, `ActionDispatcher` sabit tablodan çağırır. `shell=True`, `eval`, keyfî URL/path **yok**.
- Kullanıcıya dönük metin ve dokümantasyon Türkçe; sınıf/fonksiyon adları İngilizce.
- Olumsuz sonucu başarı gibi gösterme; hata kodu ile dön (`domain/errors.py`).

## Platform
Geliştirme ortamları: Linux (Arch), Windows, macOS. Bir özellik yalnızca bir OS'te denendiyse `docs/testing.md` platform tablosuna yaz; "test edildi" deme.

## Çıktı formatı
Her anlamlı iş sonunda: ne değişti (dosya yolları), ne çalıştırıldı (komut + sonuç), ne test edilmedi, sıradaki adım ve sahibi, hoca kararına bağlı bekleyen iş.
