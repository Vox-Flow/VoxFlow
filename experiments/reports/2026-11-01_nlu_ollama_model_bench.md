# Deney: Ollama NLU model kıyası — nlu_dev_v1 (zero-shot ve few-shot)

| Alan | Değer |
|---|---|
| Tarih | 2026-11-01 |
| Koşan | Melike Nesrin Zaman |
| İzlek | NLU (Qwen/Gemma/Llama eğitilmez; hazır model, JSON modu) |
| Veri | datasets/manifests/nlu_dev_v1.jsonl (n = 66, dondurulmuş) |
| Betik | experiments/nlu/bench_ollama_quick.py, temperature 0, num_predict 120 |
| Donanım | RTX 3050 Ti Laptop 4 GB, i7 11. nesil, 15 GB RAM (Linux) |
| Modeller | Ollama varsayılan q4 kuantizasyon; hiçbir model bu deney için indirilmedi |

## Sonuçlar (n = 66)
| Model | Prompt | intent acc | slot EM | geçerli JSON | gecikme ort. | p50 | max |
|---|---|---|---|---|---|---|---|
| **kurallı (referans)** | – | **0.955** | **0.924** | – | **0.0001 s** | | |
| qwen2.5:1.5b | zero-shot | 0.697 | 0.545 | 1.000 | 0.17 s | 0.15 | 0.30 |
| qwen2.5:3b | zero-shot | 0.742 | 0.636 | 0.939 | 0.59 s | 0.56 | 1.29 |
| gemma3:4b | zero-shot | 0.742 | 0.697 | 1.000 | 0.84 s | 0.80 | 1.47 |
| llama3.2:3b | zero-shot | 0.742 | 0.621 | 0.955 | 0.28 s | 0.26 | 0.86 |
| **qwen2.5:3b** | **few-shot (8 örnek)** | **0.879** | **0.773** | **1.000** | **0.20 s** | 0.18 | 0.45 |
| gemma3:4b | few-shot | 0.803 | 0.773 | 1.000 | 0.94 s | 0.84 | 1.74 |
| llama3.2:3b | few-shot | 0.818 | 0.682 | 1.000 | 0.21 s | 0.18 | 0.55 |

## Gözlemler
- Hiçbir küçük LLM tek başına kurallı yorumlayıcıya yetişmiyor. Bu, **hibrit** kararını (ADR-009: önce kural, bilinmezse LLM) destekler.
- Few-shot örnekler qwen2.5:3b'yi +14 puan yükseltti; prompt tasarımı model seçimi kadar önemli.
- qwen2.5:3b: en iyi doğruluk ve en düşük gecikme birlikte. Hataları: unsupported→create_task/open_app (kapsam dışı isteği "yapabilirim" sanma) ve bağlam dışı "evet"→affirm.
- gemma3:4b: 4 GB GPU'da en yavaş (~0.9 s); unsupported'ı open_app sanma eğilimi; `youtube'u aç`'ı zero-shot'ta open_app dedi.
- llama3.2:3b: hızlı ama create_note'u sık sık unsupported sayıyor.
- Tüm modellerde ortak zayıflık: **unsupported** ve **unknown** ayrımı. Güvenlik açısından validator yine de hiçbirinin izinsiz işlem başlatmasına izin vermez; sorun yalnızca kullanıcıya yanlış soru sorulması.

## Sınırlılıklar
- Tek makine, 4 GB VRAM; 7B modeller test edilmedi. 66 örnek küçük; ±5 puan farklar anlamlı değil.
- Prompt elle yazıldı, optimize edilmedi. Gecikmeler Linux/CUDA; Windows/macOS farklı olabilir.

## Öneri (Helin'in makinesi: 6 GB VRAM, 64 GB RAM, i7 13. nesil)
1. **Varsayılan: `qwen2.5:3b`** (1.9 GB). Hızlı, Türkçe komutları en iyi anlayan, 6 GB'a rahat sığar; hibrit modda LLM'e yalnızca kuralın bilmediği cümleler gider.
2. Deneme adayı: `qwen2.5:7b` (~4.7 GB, 6 GB'a sığar). Doğruluk artışı beklenir, gecikme ~2–3×. Helin kendi makinesinde aynı betikle ölçsün; 3b'den belirgin iyi değilse 3b kalır.
3. gemma3:4b bu görevde avantaj göstermedi; gemma3:12b (~8 GB) 6 GB VRAM'e sığmaz, CPU'ya taşar ve yavaşlar. Önerilmez.
