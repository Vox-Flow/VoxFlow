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

## ADR-007 — Fine-tuning hedefi AÇIK (hoca yanıtı bekleniyor)
- **Durum:** ASR (Whisper) mi NLU (Qwen LoRA) mi kararlaştırılmadı. Her iki izlek için yalnızca adaptör + veri şeması + değerlendirme iskeleti hazırlanır. Büyük model indirme/eğitim yok.
- **Donanım notu (ölçüldü):** RTX 3050 Ti Laptop 4 GB VRAM, 15 GB RAM. Bu, Qwen 7B tam fine-tune için yetersiz; QLoRA 0.5B–1.5B veya Whisper tiny/base fine-tune gerçekçi. Kesin seçim hoca yanıtı + bellek testi + ekip onayı ile.
