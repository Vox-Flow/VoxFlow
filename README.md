# VoxFlow — Yerel Türkçe Sesli Bilgisayar Asistanı

Bilgisayar Mühendisliği Tasarım dönem projesi, **61. Grup** (Helin Mengüloğul, İremsu Pala, Melike Nesrin Zaman).
Resmî konu: *Ses Kayıtlarını Otomatik Yazıya Dönüştürme Uygulaması*.

Kullanıcı terminalde Enter ile ses kaydını başlatıp bitirir → konuşma yerel ASR ile Türkçe metne çevrilir →
niyet yorumlanır ve **doğrulanır** → yalnızca izin verilen işlem yapılır → terminalde (ve varsa yerel TTS ile) geri bildirim verilir.

> Durum (2026-11-27): **Faz 1–3 tamamlandı ve ölçüldü**; `v0.1.0` yayımlandı. Ses hattı gerçek
> mikrofon ve Whisper `small` ile uçtan uca çalıştırıldı. Fine-tuning kararı: **Whisper ana izlek**,
> Qwen eğitilmeden hibrit NLU (ADR-008/009). Uyarlama verisi **FLEURS Türkçe** (ADR-011 — Common Voice
> Hugging Face'ten kaldırıldı). **Sırada:** Whisper uyarlaması ve uyarlama sonrası WER karşılaştırması.
>
> **Ölçülen NLU sayıları.** Geliştirme kümesinde (`nlu_dev_v1`, n=66) kurallı çözümleyici 1,000 niyet
> doğruluğu veriyor; ancak o kümenin hataları kuralları düzeltmek için kullanıldığı için bu sayı
> genelleme başarımı değildir. Düzeltmelerde hiç kullanılmamış tutulmuş kümede (`nlu_test_v2`, n=36)
> **0,722**. Raporda geçen sayı budur. Ayrıntı: `experiments/reports/2026-11-27_nlu_holdout_v2.md`.

## Hızlı başlangıç (internet ve model gerektirmez)
```bash
uv venv .venv && uv pip install -e '.[dev]'
.venv/bin/voxflow --text "görev ekle" --text "Matematik ödevi"   # çok turlu akış
.venv/bin/voxflow chat                                             # etkileşimli metin modu
.venv/bin/voxflow info                                             # adaptör/ortam durumu
.venv/bin/python -m pytest                                         # 119 test, <5 sn
```
Ayrıntılı kurulum, çevrimdışı mod ve ses/ASR seçenekleri: [`docs/setup.md`](docs/setup.md).

## Neler yapabilir (ilk sürüm kapsamı)
| Komut örneği | Niyet | Not |
|---|---|---|
| `yarın için matematik ödevi görevi ekle` | create_task | tarih isteğe bağlı; tarih **tahmin edilmez** |
| `görev ekle` → `Fizik ödevi` | create_task (çok turlu) | eksik başlık sorulur |
| `not al süt almayı unutma` | create_note | |
| `görevleri listele`, `yarınki görevleri göster` | list_tasks | |
| `geçmişi göster` | show_history | metin + sonuç + zaman; ham ses yok |
| `geçmişi sil` → `evet`/`hayır` | clear_history | **onay zorunlu** |
| `firefox aç`, `hesap makinesini aç` | open_app | yalnızca `config/apps.json` allowlist |
| `youtube'u aç` | open_website | yalnızca `config/sites.json` allowlist; "yüklendi" denmez |
| `vazgeçtim`, `iptal et` | cancel | yalnızca bekleyen işlem iptal edilir |
| `görevi sil`, `bilgisayarı kapat` | unsupported | desteklenmediği söylenir, izinli örnekler gösterilir |

Bilinçli olarak **yok**: görev/not silme-düzenleme-tamamlama, serbest komut çalıştırma, keyfî URL, sürekli dinleme/wake word.

## Mimari (özet)
`CLI → AudioCapture → SpeechRecognizer → IntentInterpreter → DialogueManager → CommandValidator → ActionDispatcher → JsonStore → Presenter`
Port/adaptör yapısı sayesinde ASR (mock / faster-whisper) ve NLU (kurallı / Ollama-Qwen / ileride fine-tuned) değiştirilebilir. Bkz. [`docs/architecture.md`](docs/architecture.md), [`docs/interfaces.md`](docs/interfaces.md).

## Güvenlik ve gizlilik
- LLM/kural çıktısı asla komut üretmez; yalnızca `Intent` seçer, Python tarafı allowlist ile doğrular, dispatcher sabit tablodan fonksiyon çağırır.
- `shell=False`, argv config'ten; kullanıcı metni URL'ye ya da komuta girmez. Konuşma metni güvenilmez girdidir (prompt injection = düz not metni).
- Tüm modeller yerel; hiçbir veri üçüncü taraf API'ye gitmez. TTS/telemetri varsayılan kapalı.
- Ham ses yalnızca bellekte; kalıcı geçmişte metin, sonuç, zaman damgası. Veri dizini (`~/.local/share/voxflow` vb.) ve `config/*.json` **git'e girmez**.
- JSON depo: atomik yazım, `.bak` yedeği, bozuk dosyada açık hata (`E_STORE_CORRUPTED`).

## Depo yapısı
```
src/voice_assistant/   domain/ ports/ adapters/{audio,asr,nlu,tts,platforms,storage} services/ cli.py wiring.py config.py
tests/                 unit/ integration/  (model/ses gerektirmez)
config/                *.example.json (gerçek dosyalar gitignore)
datasets/              manifests/ (yalnızca sentetik örnek)  docs/dataset_protocol.md
experiments/           nlu/eval_rule_based.py  asr/eval_wer.py  reports/ (boş: henüz ölçüm yok)
docs/                  architecture, interfaces, decisions (ADR), testing, setup, team_tasks, traceability, dataset_protocol
```

## Model eğitimi — karar verildi (2026-10-20)
Hoca: "hazır bir modeli kendi verilerinizle fine-tune etmeniz yeterli." Ekip kararı: **Whisper (`openai/whisper-base`) FLEURS Türkçe ile fine-tune edilir** (ADR-011; kendi gönüllü kayıtlarımız ikinci aşama) (WER/CER + uçtan uca işlem doğruluğu, konuşmacı-ayrık test). NLU tarafında Qwen2.5 **eğitilmez**; Ollama üzerinden hazır haliyle, hibrit modda (önce kural, bilinmezse LLM) isteğe bağlı kullanılır. Ayrıntı ve riskler: `docs/decisions.md` ADR-008, ADR-009. **Durum:** Whisper `base`/`small` ve Qwen2.5 modelleri indirildi ve ölçüldü; uyarlama (fine-tune) **henüz yapılmadı**, uyarlama sonrası karşılaştırma bekliyor.

## Ekip
Görev dağılımı ve kabul kriterleri: [`docs/team_tasks.md`](docs/team_tasks.md). Her PR başka bir üye tarafından gözden geçirilir.
