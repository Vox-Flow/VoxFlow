# datasets/
- `manifests/nlu_synthetic_dev.jsonl` — elle yazılmış sentetik komut örnekleri (git'te). Gerçek veri değildir; şema ve betik testi içindir.
- `manifests/nlu_dev_v1.jsonl` — **dondurulmuş NLU test kümesi** (66 örnek, team_written, 2026-11-01): her niyet ≥5 söyleyiş, 16 unsupported/unknown, bağlamlı örnekler (pending title/content/app, pending_confirmation). Kural ve Qwen karşılaştırması bu kümede yapılır; örnek eklenirse `v2` olarak yeni dosya açılır.
- `manifests/asr_synthetic_example.jsonl` — ASR manifest şema örneği (ses dosyaları yok).
- Gerçek ses (`datasets/audio/`, `datasets/raw/`) ve `*_real*.jsonl` gitignore'dadır.
Protokol: `docs/dataset_protocol.md`.
