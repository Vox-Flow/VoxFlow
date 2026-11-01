# Karar Kaydı (ADR)

Her karar: bağlam, alternatifler, karar, etkiler, geri dönüş planı. Tarihler gerçek tarihtir.

## ADR-001 — Hexagonal (port/adaptör) yapı, Protocol tabanlı arayüzler (2026-10-19)
- **Bağlam:** ASR ve NLU sağlayıcıları değişebilir; hocanın fine-tune kararı belirsiz.
- **Alternatifler:** Tek dosya script; ABC miras hiyerarşisi; ağır framework.
- **Karar:** `typing.Protocol` ile yapısal arayüzler (`ports/protocols.py`), adaptörler `adapters/` altında. Mock adaptörler aynı kontratı uygular.
- **Etkiler:** Testler model olmadan koşar; Whisper/Qwen/fine-tuned model yalnızca yeni adaptördür.
- **Geri dönüş:** Protocol'ler soyutlama fazla gelirse ABC'ye çevrilebilir; adaptörler etkilenmez.

## ADR-002 — Niyet kataloğuna `affirm`/`deny` diyalog niyetleri eklendi (2026-10-19)
- **Bağlam:** `clear_history` onay gerektirir. "evet/hayır" bir eylem değil, diyalog tepkisidir.
- **Alternatifler:** Onayı DialogueManager içinde ham metinle eşleştirmek (NLU'yu atlar); `confirm_clear_history` gibi ayrı eylem niyeti.
- **Karar:** `Intent.AFFIRM` / `Intent.DENY` **yalnızca bekleyen onay varken** üretilir; bağlam yoksa "evet" → `unknown`. Eylem niyetleri kümesi (`ACTION_INTENTS`) değişmedi; kapsam genişlemedi.
- **Etkiler:** NLU kıyaslamasında (kural vs Qwen) onay turları da ölçülebilir.
- **Geri dönüş:** Niyetler kaldırılıp eşleştirme DialogueManager'a taşınabilir.

## ADR-003 — Görevde tarih isteğe bağlı, başlık zorunlu; tarih tahmin edilmez (2026-10-19)
- **Bağlam:** "görev ekle → ad sor" kabul akışı; "tarih eksikse sessizce tahmin etme" kuralı.
- **Karar:** `title` zorunlu (eksikse sorulur). `date` isteğe bağlı; verilmezse `null` olarak kaydedilir ve yanıt "tarihsiz" der. Anlaşılamayan tarih ifadesi hata üretir, bugüne çevrilmez.
- **Geri dönüş:** Tarih zorunlu istenirse `REQUIRED_PARAMETERS[CREATE_TASK]`'a `date` eklenir; akış otomatik olarak soru sorar.

## ADR-004 — Geçmişe yalnızca sonuçlanmış turlar yazılır (2026-10-19)
- **Karar:** `needs_clarification` / `needs_confirmation` ara turları kalıcı geçmişe yazılmaz; başarı, hata, iptal, desteklenmiyor, anlaşılamadı yazılır. Ham ses hiçbir zaman yazılmaz.
- **Gerekçe:** Geçmiş "gerçek işlem sonucu" içindir; ara sorular gürültüdür.

## ADR-005 — Kayıt kontrolü Enter ile başlat / Enter ile bitir (2026-10-19)
- **Bağlam:** Üç OS'de ham tuş yakalama (termios/msvcrt) farklı ve kırılgan.
- **Karar:** Faz 2'de `voxflow listen`: Enter → kayıt başlar, Enter → biter. Push-to-talk ya da wake word yok.
- **Geri dönüş:** `readchar`/`pynput` ile tek tuş desteği isteğe bağlı eklenebilir; kontrat değişmez.

## ADR-006 — Allowlist konfigürasyonu: `config/apps.json`, `config/sites.json` (2026-10-19)
- **Karar:** Uygulama komutu platform başına sabit argv listesi; `shell=False`. Site URL'leri yalnızca http/https; kullanıcı metni asla URL'ye girmez. Gerçek dosyalar `.gitignore`'da; `*.example.json` sürümlenir.

## ADR-007 — Fine-tuning hedefi (KAPATILDI, bkz. ADR-008) (2026-10-19 → 2026-10-20)
- **Durum:** 2026-10-20'de hoca yanıtı geldi: "Hazır bir modeli kendi verilerinizle fine-tune etmeniz yeterli; planladığınız şekilde ilerleyebilirsiniz." Yöntem seçimi ekibe bırakıldı. Karar ADR-008'de.
- **Donanım notu (ölçüldü):** RTX 3050 Ti Laptop 4 GB VRAM, 15 GB RAM.

## ADR-008 — Ana fine-tuning izleği: Whisper (ASR) (2026-10-20)
- **Bağlam:** Hoca "hazır model + kendi veri ile fine-tune" şartı koydu, hangi katman olduğunu ekibe bıraktı. Ders başlığı ASR. 4 GB VRAM.
- **Alternatifler:** (a) Qwen LoRA (komut→JSON): veri üretimi kolay, eğitim hızlı; ama ders başlığıyla bağı zayıf ve kurallı NLU zaten çalışıyor, "neden eğittiniz" sorusuna zayıf cevap. (b) İki izlek paralel: 3 kişilik ekipte dağınıklık riski. (c) Whisper.
- **Karar:** Tek ana izlek **Whisper fine-tune**. Taban `openai/whisper-base` (74M); tam fine-tune fp16 + gradient checkpointing 4 GB'a sığmalı; `small` yalnızca LoRA ile düşünülür. Eğitim HF transformers; çıkarım için CTranslate2'ye çevrilip mevcut `FasterWhisperRecognizer`'a takılır.
- **Veri:** ≥8–10 konuşmacı × ~100 komut × ~3 sn ≈ 1 saat hedef (ölçülmüş değil, hedef). Konuşmacı-ayrık split. İsteğe bağlı destek: Common Voice TR (lisans/erişim koşulları kullanılmadan önce doğrulanacak). Açık izin formu zorunlu (`docs/consent_form_tr.md`).
- **Metrikler:** WER/CER (konuşmacı-ayrık test), gecikme, bellek; ayrıca uçtan uca ASR→kurallı NLU işlem doğruluğu. Baseline = aynı testte fine-tune edilmemiş base.
- **Risk (açıkça):** Whisper Türkçeyi zaten iyi bilir; küçük veriyle genel WER'de büyük düşüş beklenmez. Kazanç alan sözcükleri (uygulama/site adları, komut kalıpları), kendi mikrofon/konuşmacılar ve kısa cümle halüsinasyonlarında aranır. Fark küçük çıkarsa da rapora yazılır.
- **Geri dönüş:** Eğitim 4 GB'a sığmazsa `tiny` ya da LoRA; o da olmazsa Colab/Kaggle T4 — yalnızca izin formunda bulut işleme maddesi varsa.

## ADR-009 — NLU: Qwen eğitilmez, hibrit kullanılır (2026-10-20)
- **Karar:** Qwen2.5 (Ollama, hazır) **fine-tune edilmez**; yalnızca yapılandırılmış JSON üreten isteğe bağlı IntentInterpreter adaptörüdür. Üç NLU modu: `rule_based` (varsayılan, bağımlılıksız), `ollama`, `hybrid` (önerilen: önce kural, `unknown` dönerse Qwen). Her çıktı `CommandValidator`'dan geçer.
- **Gerekçe:** Kural anında ve belirleyici; LLM yalnızca serbest söyleyişte değer katar; Ollama yoksa sistem çalışmaya devam eder; injection yüzeyi küçülür.
- **Model seçimi (ölçüldü, 2026-11-01):** nlu_dev_v1'de qwen2.5 1.5b/3b, gemma3 4b, llama3.2 3b kıyaslandı (`experiments/reports/2026-11-01_nlu_ollama_model_bench.md`). Hiçbiri tek başına kurallıya (0.955) yetişmedi → hibrit doğrulandı. Varsayılan aday **qwen2.5:3b** (few-shot 0.879, 0.2 s); 6 GB VRAM makinede `qwen2.5:7b` denenecek. Gemma3 avantaj göstermedi.
- **Qwen fine-tune:** yapılmaz; "ileriki çalışma" olarak rapora yazılır.
