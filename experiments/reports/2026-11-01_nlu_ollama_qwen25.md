# Deney: Hibrit NLU (Kurallı + Ollama Qwen2.5 3B) — nlu_dev_v1

| Alan | Değer |
|---|---|
| Tarih | 2026-11-01 |
| Koşan | Helin Mengüloğul |
| İzlek | NLU (ADR-009: Qwen eğitilmez; hazır Qwen2.5 Ollama hibrit mod) |
| Model | qwen2.5:3b (Ollama, 1.9 GB) |
| Sağlayıcı | hybrid (RuleBasedInterpreter + OllamaInterpreter) |
| Veri | datasets/manifests/nlu_dev_v1.jsonl (n = 66, dondurulmuş test) |
| Donanım | Windows 11, RTX GPU, i7, Python 3.12 |
| Sıcaklık / Num Predict | temperature=0.0, format="json" |

## Metrikler
| Metrik | Kurallı (Tek Başına) | Hibrit (Kural + Qwen2.5 3B) |
|---|---|---|
| intent accuracy | 1.0000 (66/66) | 1.0000 (66/66) |
| macro-F1 | 1.0000 | 1.0000 |
| slot exact match | 1.0000 (66/66) | 1.0000 (66/66) |
| ortalama gecikme | 0.087 ms | 630.94 ms |

## Gözlemler
- Hibrit modda kuralın kesin bildiği ifadeler anında işlenirken, serbest ve karmaşık ifadelerde Qwen2.5 3B devreye girmektedir.
- İlk çağrıda modelin GPU belleğine soğuk yüklenmesi (cold load) sırasında zaman aşımına uğrayan istekte, `OllamaInterpreter` güvenli bir şekilde `RuleBasedInterpreter` fallback'ine düşmüş ve sistem çökmeden %100 doğrulukla süreci tamamlamıştır (ADR-009 dayanıklılık prensibi doğrulandı).
- Şema dışı anahtarlar, keyfî kodlar veya prompt injection girişimleri `IntentResult` sözleşmesi ve `CommandValidator` tarafından elenmektedir.
