# Kurulum ve Çevrimdışı Çalışma

## Gereksinimler
- Python ≥ 3.11 (geliştirme ortamı: 3.14.7, Arch Linux). `uv` önerilir.

## Çekirdek (ses/LLM olmadan)
```bash
uv venv .venv
uv pip install -e '.[dev]'
cp config/app.example.json config/app.json      # isteğe bağlı; yoksa example kullanılır
cp config/apps.example.json config/apps.json    # izinli uygulamalar (platform komutlarını düzenleyin)
cp config/sites.example.json config/sites.json  # izinli siteler
.venv/bin/voxflow --text "görev ekle" --text "Matematik ödevi"
.venv/bin/voxflow chat
.venv/bin/voxflow info
```
Veri dizini: `$VOXFLOW_DATA_DIR` ya da Linux `~/.local/share/voxflow`, Windows `%APPDATA%\voxflow`, macOS `~/Library/Application Support/voxflow`.

## Ses + ASR (Faz 2, isteğe bağlı)
```bash
uv sync --extra dev --extra audio --extra asr
uv run --extra audio --extra asr voxflow listen     # ya da: .venv/bin/voxflow listen
```
**Dikkat:** `uv run` extras verilmeden çalıştırılırsa ortamı senkronlar ve ses/ASR paketlerini **kaldırır**. Her zaman `--extra audio --extra asr` ekleyin veya doğrudan `.venv/bin/voxflow` kullanın.

**GPU:** faster-whisper GPU için cuBLAS 12 ve cuDNN 9 ister. Bulunamazsa adaptör uyarı verip **otomatik CPU'ya düşer**; `base` modeli CPU'da da gerçek zamanlıdan hızlıdır. GPU istiyorsanız (Linux) `uv pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` (~700 MB) ya da `config/app.json` → `"device": "cpu"` ile uyarıyı susturun.
`config/app.json` → `"asr": {"provider": "faster_whisper", "model_size": "base", "compute_type": "int8"}`.

**Model indirme (tek sefer, internetli, ekip onayıyla):** faster-whisper modelini önceden indirin; adaptör `local_files_only=True` ile çalışır, çevrimdışı yeniden indirmeye kalkmaz. `tiny` ≈ 75 MB, `base` ≈ 145 MB (CTranslate2 int8). Hangi boyutun indirileceğine ekip karar verir; bu depo indirmeyi otomatik başlatmaz.

## Uçak modu kontrol listesi
1. İnterneti kapat.
2. `voxflow info` → ASR hazır: True olmalı.
3. `voxflow --text "görevleri listele"` çalışmalı.
4. `voxflow listen` → Enter, konuş, Enter → transkript + işlem.
5. `youtube aç` → "açma isteği gönderildi" der; sayfa yüklenmez, bu beklenen davranıştır.

## NLU (Faz 3, isteğe bağlı)
Ollama kurulu ve `qwen2.5` yerelde mevcutsa `"nlu": {"provider": "ollama"}`. Sunucu kapalıysa kurallı yorumlayıcıya düşer (uyarı verir).

## Whisper eğitim ağırlıkları (Faz 4, ekip onayıyla, tek sefer, internetli)
`openai/whisper-base` HF ağırlıkları ≈ 290 MB:
```bash
uv sync --extra dev --extra train
uv run python -c "from transformers import WhisperForConditionalGeneration as M, WhisperProcessor as P; \
  M.from_pretrained('openai/whisper-base'); P.from_pretrained('openai/whisper-base')"
```
Sonrasında `train_whisper.py` `local_files_only=True` ile çalışır; çevrimdışı yeniden indirmeye kalkmaz.
