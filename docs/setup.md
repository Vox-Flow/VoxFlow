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

## Terminal sunumu (isteğe bağlı)
```bash
uv sync --extra dev --extra ui          # rich kurar
.venv/bin/voxflow --ui rich chat        # renkli panel/durum çıktısı
.venv/bin/voxflow --ui plain chat       # düz metin (varsayılan davranış)
```
`--ui auto` (varsayılan): terminalde rich kuruluysa renkli, boruya/dosyaya yazarken düz metin —
`voxflow ... > kayit.txt` çıktısı kaçış kodu içermez. rich kurulu değilse uygulama çalışmaya
devam eder, yalnızca düz metne düşer.

## Ses + ASR (Faz 2, isteğe bağlı)
```bash
uv sync --extra dev --extra audio --extra asr
uv run --extra audio --extra asr voxflow listen     # ya da: .venv/bin/voxflow listen
```
**Dikkat:** `uv run` extras verilmeden çalıştırılırsa ortamı senkronlar ve ses/ASR paketlerini **kaldırır**. Her zaman `--extra audio --extra asr` ekleyin veya doğrudan `.venv/bin/voxflow` kullanın.

**GPU:** faster-whisper GPU için cuBLAS 12 ve cuDNN 9 ister. Bulunamazsa adaptör uyarı verip **otomatik CPU'ya düşer**; `base` modeli CPU'da da gerçek zamanlıdan hızlıdır. GPU istiyorsanız (Linux) `uv pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` (~700 MB) ya da `config/app.json` → `"device": "cpu"` ile uyarıyı susturun.
`config/app.json` → `"asr": {"provider": "faster_whisper", "model_size": "base", "compute_type": "int8"}`.

**Alan sözlüğü ipucu:** adaptör Whisper'a `initial_prompt` olarak komut kalıplarını ve izinli uygulama/site adlarını verir (otomatik; `asr.initial_prompt` ile özelleştirilebilir). Fine-tune değildir, yabancı adlarda ve kısa komutlarda yardımcı olur.

**Model boyutu:** `base` (~145 MB int8) Türkçe kısa komutlarda zayıf kalabilir; `small` (~480 MB int8) belirgin daha iyi ve CPU'da hâlâ gerçek zamanlıdan hızlı. Ekip kararı: ikisi aynı 10 cümlede karşılaştırılır.

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

## Donanıma bağlı ölçümler ve makine devri

Proje iki farklı makinede yürütülmektedir ve bazı sayılar makineye bağımlıdır. Hangi
sonucun taşınabilir, hangisinin yeniden ölçülmesi gerektiği aşağıdadır.

| Ölçüm | Donanıma bağlı mı | Not |
|---|---|---|
| Niyet doğruluğu, makro F1, slot tam eşleşme | Hayır | Makineden bağımsız, olduğu gibi kullanılabilir |
| Geçerli LLM yanıtı oranı | Hayır | Model ve istem belirler |
| WER / CER | Hayır | Model ve veri belirler |
| **Gecikme (LLM ve ASR)** | **Evet** | Aşağıya bakınız |
| Fine-tune yapılabilirliği | **Evet** | Ekran kartı belleğiyle sınırlı |

**Ölçümlerin yapıldığı makine (Melike):** RTX 3050 Ti Laptop, 4 GB ekran kartı belleği,
15 GB RAM. `cuBLAS 12` kurulu olmadığı için hem Whisper hem Ollama **işlemci üzerinde**
çalışmaktadır. Bu nedenle 25 Kasım ölçümündeki 6,4 saniyelik LLM gecikmesi bu makineye
özgüdür ve genel bir sonuç olarak sunulmamalıdır.

**Model çalıştırma ve uyarlama makinesi (Helin):** 6 GB ekran kartı belleği, 64 GB RAM.
Bu makinede yeniden ölçülmesi gerekenler:

1. **LLM gecikmesi** — `uv run python experiments/nlu/eval_rule_based.py
   datasets/manifests/nlu_dev_v1.jsonl --provider ollama --model qwen2.5:3b --json`.
   Doğruluk değerleri aynı çıkmalı; yalnızca gecikme düşmelidir.
2. **Whisper gecikmesi** — GPU için `uv pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`
   (yaklaşık 700 MB). Kurulu değilse uyarı verilip işlemciye düşülür.
3. **Uyarlama (fine-tune)** — 6 GB bellekte `whisper-base` tam uyarlaması beklenmektedir;
   `small` sınırdadır ve gerekirse LoRA ile yapılmalıdır. Konfigürasyon:
   `experiments/asr/configs/whisper_base_ft.yaml`. Önce `--dry-run` ile doğrulayın.

**Taşınmayan iş:** ses kaydı toplama güçlü makine gerektirmez; mikrofonu olan herhangi
bir bilgisayarda `voxflow record` ile yapılabilir.
