# Deney: Whisper-base uyarlama ortamı hazırlık kontrolü ve VRAM ölçümü (#8 adım 3, #50)

| Alan | Değer |
|---|---|
| Tarih | 2026-11-27 |
| Koşan | Helin |
| İzlek | ASR |
| Model + sürüm | openai/whisper-base (HF, `model.safetensors` 290.403.936 bayt), fp32 ağırlık + fp16 autocast |
| Veri manifesti + sürüm | yok — **gerçek veri kullanılmadı** (rastgele tensör, ölçüm amaçlı) |
| Split | yok |
| Config | experiments/asr/configs/whisper_base_ft.yaml @ sha256:1faf657d200f |
| Seed | ayarlanmadı (rastgele girdi; ölçüm bellek/süre içindir) |
| Donanım | NVIDIA GeForce RTX 4050 Laptop GPU, 6141 MiB VRAM, sürücü 581.80; Windows 11 Pro; torch 2.11.0+cu128, Python 3.12 |

## Ortam kanıtı
| Kontrol | Sonuç |
|---|---|
| `torch.cuda.is_available()` | **True**, kart adı: NVIDIA GeForce RTX 4050 Laptop GPU |
| `train_whisper.py <config> --dry-run` | hatasız (çıkış 0); manifestler henüz yok, "veri bekleniyor" uyarısı |

## Metrikler (sentetik: batch × 80×3000 özellik, 32 token etiket, AdamW, GradScaler)
| Ayar | Model yüklü (nvidia-smi) | Tepe ayrılan (torch rezerve) | Tepe nvidia-smi | Adım süresi (ısınma sonrası) |
|---|---|---|---|---|
| **Config değerleri:** batch 8, fp16, gradient_checkpointing, encoder açık | 878 MiB | 1824 MiB | 2448 MiB | **0,57 sn** (ilk adım 1,90 sn) |
| batch 4 | 940 MiB | 1474 MiB | 2098 MiB | 0,29 sn |
| batch 8, `freeze_encoder: true` | 940 MiB | 1330 MiB | 1954 MiB | 0,35 sn |

- **Boşta VRAM:** 502–631 MiB / 6141 MiB (masaüstü + tarayıcı; Ollama modeli boşaltılmış).
- **Dry-run tepe VRAM:** ölçülemez — `--dry-run` torch'u içe aktarmıyor ve model yüklemiyor. Yerine yukarıdaki sentetik adım ölçüldü.
- **Tahmini adım süresi:** config değerleriyle mikro-batch (8) ≈ 0,57 sn; `gradient_accumulation_steps: 2` ile bir optimizer adımı (etkin batch 16) ≈ **1,1 sn**. Bir epoch süresi = ⌈N/16⌉ × 1,1 sn (N = eğitim örneği sayısı; veri gelince hesaplanacak).

## Sonuç: config 6 GB'a sığıyor mu?
**Evet, değişiklik gerekmiyor.** `whisper_base_ft.yaml` değerleri (batch 8, fp16, gradient checkpointing, encoder dondurulmamış) tepede ≈ 2,4 GiB kullanıyor; kartta ≈ 3,7 GiB boşluk kalıyor. `freeze_encoder` ya da batch düşürme gerekmedi. Config'e dokunulmadı.

## Gözlemler ve sınırlılıklar
- Ölçüm **sentetik**: gerçek ses uzunluğu dağılımı, gerçek etiket uzunluğu, veri yükleme/özellik çıkarma ve değerlendirme (`generate`) maliyeti **ölçülmedi**. Gerçek eğitimde adım süresi veri yükleyiciye bağlı olarak artabilir.
- "Tepe nvidia-smi" adımların sonunda okundu; gerçek tepe için torch'un `max_memory_reserved` değeri (1824 MiB) esas alınmalı.
- İlk adım ısınma nedeniyle yavaş (1,90 sn); ortalamaya katılmadı.
- Tek koşu, tek makine, 4 adım/ayar; varyans ölçülmedi.
- Ortam notları (Windows):
  - PyPI'dan gelen torch Windows'ta CPU-only (`2.14.1+cpu`); CUDA için `--index-url https://download.pytorch.org/whl/cu128` ile elle kurulum gerekti. `uv sync` bunu CPU sürümüne geri çevirir.
  - `uv sync --extra asr --extra dev` torch'u kurmaz; torch `train` extra'sında.
  - Betik `--config` bayrağı değil konumsal argüman bekler.
  - HF Hub önbelleği Windows'ta sembolik bağ desteği olmadan (Developer Mode kapalı) çalışıyor; ilk indirme `snapshot_download` ile sessizce eksik kaldı, dosyalar tek tek `hf_hub_download` ile indirildi.

## Sonuç ve sonraki adım
Ortam hazır: veri (İremsu, PR #49) geldiğinde eğitim doğrudan başlayabilir. Sonraki adım: gerçek manifestle kısa bir koşuda gerçek adım süresi ve tepe VRAM'in yeniden ölçülmesi.
