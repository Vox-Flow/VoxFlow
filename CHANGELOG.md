# Değişiklik Günlüğü

Biçim: [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/), sürümleme
[SemVer](https://semver.org/lang/tr/). Tarihler YYYY-AA-GG.

## [Yayımlanmamış]

## [0.9.0-rc] — 2026-11-27

İlk ölçülmüş ASR sayılarının elde edildiği sürüm. `v1.0` için eksik olan tek şey
uyarlama (fine-tune) sonucudur; ölçülmemiş iddiayla sürüm etiketi atılmaz.

### Eklendi
- **FLEURS Türkçe veri hattı** (`experiments/asr/prepare_fleurs.py`): 32 bit float
  WAV'ı PCM-16'ya çevirir, protokol şemasında manifest üretir, ffmpeg gerektirmez
- **Taban ASR ölçümü**: Whisper `base` WER 0,2572 · CER 0,0673; `small` WER 0,1350 ·
  CER 0,0339 (n=743, 2,61 saat, CPU/int8)
- **Tutulmuş NLU test kümesi** (`nlu_test_v2`, n=36): kuralların düzeltilmesinde hiç
  kullanılmadı. Kurallı çözümleyici burada niyet 0,722 veriyor — raporda geçecek sayı bu
- **Cümle sızıntısı denetimi** (`validate_manifest.py`): konuşmacı kimliği olmayan
  kaynaklarda bölme bağımsızlığının tek kanıtı
- **Giriş aygıtı seçimi**: `voxflow devices` komutu, `listen`/`record` için `--device`,
  `config/app.json` → `audio.device`
- **Sunum katmanı portu**: `ResponsePresenter`, `--ui auto|plain|rich`
- Uçtan uca ölçüm araçları: `load_wav()`, `eval_wer.py --emit-hyp/--initial-prompt`,
  `eval_pipeline.py --provider`

### Düzeltildi
- **Güvenlik:** LLM'in uydurduğu ISO tarih doğrulamadan geçiyordu; model artık `date`
  anahtarı döndürse de atılıyor, tarih her zaman `date_text` → `find_date` yolundan çözülüyor
- Hibrit yönlendirme ölçütü daraltıldı: `unknown` bir başarısızlık işareti değil geçerli
  bir yanıttır; LLM'e yönlendirilince doğru yanıtlar bozuluyordu (0,985 → 1,000)
- ASR'nin tek harflik hatalarına tolerans (`görevleri listela` → `list_tasks`)
- Sessiz kayıt hatası artık ne yapılacağını söylüyor (hangi aygıt, ölçülen RMS, yönlendirme)

### Değişti
- Uyarlama verisi Common Voice'tan FLEURS'e geçti (ADR-011) — Common Voice Ekim 2025'te
  Hugging Face'ten kaldırıldı, Mozilla Data Collective'e taşındı
- `transformers` sürümüne `<5` tavanı: 5.x, `train_whisper.py`'nin kullandığı v4 API'sini
  değiştiriyor

### Bilinen eksikler
- Whisper uyarlaması henüz koşulmadı (#63)
- Uçtan uca **sesli** işlem başarı oranı ölçülmedi; FLEURS bu iş için uygun değil
  (haber cümleleri, NLU altın etiketi yok) — kendi komut kayıtlarımız gerekiyor (#41)
- Konuşmacı-ayrıklık FLEURS'te veriden doğrulanamıyor
- Windows'ta mikrofon yolu doğrulanamadı (#12); `--device` eklendi ama orada denenmedi
- macOS hiç denenmedi

## [0.1.0] — 2026-11-18
- İlk yayım: metin modu, kurallı NLU, hibrit NLU iskeleti, güvenlik zinciri
  (allowlist + doğrulayıcı + sabit eylem tablosu), hexagonal mimari, CI.
