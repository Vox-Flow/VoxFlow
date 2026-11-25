# Veri Seti Protokolü

İki ayrı manifest; aynı kayıt her ikisinde yer alabilir ama zorunlu değildir.

## ASR manifesti (`datasets/manifests/asr_*.jsonl`, satır başına JSON)
`sample_id, audio_path, transcript, speaker_id, language, duration_s, split, source, consent_or_license, quality_flags`
- `audio_path` depoda **yok** (gitignore); yalnızca yerel yol. `speaker_id` anonim (`spk_01`).
- `transcript` insan tarafından kontrol edilmiş; ASR çıktısı otomatik etiket **değildir**.
- `consent_or_license`: `team_consent_v1` (ekip içi açık izin formu) ya da dış veri lisansı (örn. Common Voice — lisans/erişim koşulları kullanılmadan önce doğrulanacak).
- `quality_flags`: `noise`, `clipping`, `silence`, `truncated`, `ok`.

## NLU manifesti (`datasets/manifests/nlu_*.jsonl`)
`sample_id, utterance, intent, slots, dialogue_context, split, source`
- `intent` ∈ katalog (`domain/schemas.py::Intent`); `slots` yalnızca izinli parametreler. Göreli tarihler `slots.date_text` olarak **metin** tutulur; ISO'ya değerlendirme anında, sabit bir referans günle çevrilir.
- `dialogue_context`: `null` | `{"pending": "create_task.title"}` | `{"pending_confirmation": "clear_history"}`.
- `source`: `synthetic`, `team_written`, `team_spoken_transcribed`.

## Bölme kuralları
- ASR: konuşmacı bazlı split (aynı `speaker_id` iki split'te olmaz).
- NLU: aynı cümlenin birebir/çok yakın varyantları aynı split'te kalır (ezber avantajı yok).
- Test kümesi dondurulur; baseline ve fine-tuned model **aynı** test kümesinde değerlendirilir.

## Toplama hedefleri (öneri, ölçülmüş sayı değil)
- NLU: ≥50 komut değerlendirme, ≥5 örnek/niyet, ≥10 unsupported/unknown.
- ASR: ekip içi 3 konuşmacı × 20 kısa komut başlangıç; 16 kHz mono WAV, sessiz oda + 1 gürültülü set.
- Senaryolar: farklı söyleyiş, sessizlik, mikrofon yok, gürültü, tanımsız istek.

## Gizlilik
Gerçek konuşma geçmişi (`history.json`) eğitim verisine otomatik kopyalanmaz. Yalnızca açık izinli, anonimleştirilmiş kayıtlar manifestlere girer.

## #17 kayıt oturumu protokolü — taslak v1

Bu bölüm ADR-008'in ≥8 konuşmacı hedefini somutlaştırır; yukarıdaki 3 × 20
başlangıç önerisi nihai toplama hedefi değildir. Hazırlık belgeleri:
[izin formu](consent_form_tr.md), [100 cümle](recording_sentences_tr.md),
[sekiz konuşmacılık plan ve PR #20 bağımlılığı](volunteer_speaker_plan.md).
Ekip incelemesi ve katılımcı izinleri henüz alınmadı; gerçek toplama başlamadı.

### Hazırlık ve kayıt

1. Ekip, formdaki iletişim kanalını, son silme tarihini ve erişim sorumlularını
   netleştirir. Yalnızca açıklanmış ve imzalanmış izinle kayıt yapılır. Kod–form
   eşlemesi ve imzalar repo dışında, seslerden ayrı, erişimi sınırlı tutulur.
2. Veri toplama, uygulamanın ham sesi saklamayan normal `listen` akışından ayrı
   ve açık izinli bir araştırma oturumudur. Mevcut CLI'nin kalıcı veri seti
   kaydı yaptığı varsayılmaz. Veri toplama için ayrı komut vardır:
   `voxflow record` (aşağıya bakın); `listen` akışı veri seti kaydı için kullanılmaz.
3. Gelecekte kullanılacak araç ekipçe doğrulandıktan sonra PCM 16-bit WAV,
   16 kHz, tek kanal hedeflenir. Cihaz farklı hızda kaydediyorsa kontrollü
   yeniden örnekleme yapılır; örnekleme hızını yalnızca etiket değiştirmek yasaktır.
4. Sessiz oda, sabit cihaz ve yaklaşık 15–20 cm ağız mesafesi önerilir. Cihazın
   kişisel seri numarası alınmaz. Ortam/cihaz türü ve oturum kodu yerel çizelgede
   tutulur. Ön deneme ve seviye kontrolü yapılmadan ana listeye geçilmez.
5. Her cümle ayrı dosyadır; operatör Enter ile açıkça başlatıp bitirir. Başta ve
   sonda yaklaşık yarım saniye pay bırakılır. Doğal hız ve ses düzeyi kullanılır;
   hata varsa tekrar alınır, katılımcıya baskı yapılmaz, her 25 cümlede mola verilir.
   İsteğe bağlı hafif ortam gürültüsü tekrarları ayrı etiketlenir; hedef sayıya
   yeni konuşmacı veya yeni cümle gibi eklenmez. Gürültü zorunlu değildir.
6. Adlandırma: `spk_01_s01_C001_t01.wav` — bu adlandırmayı ve manifest satırını
   `voxflow record` otomatik üretir (bkz. aşağıdaki "Kayıt aracı").
   Konuşmacı/oturum/cümle/tekrar kimliği `sample_id` içinde korunur; tekrarlar
   aynı konuşmacı ayrımında kalır. Dosya adına isim, yaş veya iletişim yazılmaz.

### Kalite ve transkripsiyon

- Boş, kesilmiş, aşırı düşük seviyeli veya kırpılmalı kayıt tekrar istenir;
  arka planda başka kişinin sesi veya kişisel bilgi varsa veri dışlanır/silinir.
  Normal sessiz komutlar için `ok`, diğerleri için uygun `quality_flags` kullanılır;
  `ok` ile hata bayrağı birlikte verilmez. Gürültülü ama anlaşılır veri `noise`
  ile tutulabilir; karar ve gerekçe yerel çizelgede belirtilir.
- Sessizlik ve mikrofon yok senaryoları teknik kontrol içindir; boş transkriptle
  ASR eğitim manifestine eklenmez. Süre dosyadan ölçülür; tahmini süre yazılmaz.
- Transkript, listedeki hedefin kopyası değil, gerçekten söylenen metindir.
  Bir ekip üyesi dinleyerek yazar, ikinci üye sesi dinleyerek doğrular. Türkçe
  karakterler korunur; noktalama/yazım tutarlı tutulur. Anlaşılamayan kayıtlar
  zorla etiketlenmez. ASR çıktısı otomatik doğru kabul edilmez.
- Cümle kimliği ve kontrol durumu ayrı yerel çizelgede tutulur; mevcut ASR
  şemasına zorunlu yeni alan eklenmez. `consent_or_license=team_consent_v1`
  ancak bu sürümde gerçek izin doğrulanmışsa yazılır; dolu alan tek başına izin
  kanıtı değildir. `source=team_spoken_transcribed`, `language=tr` kullanılır.
  Kod–izin eşlemesi manifestin içine konmaz.

### Ayrım, teslim ve silme

- Plan: 5 train / 1 val / 2 test konuşmacısı; aynı kişinin tüm oturumları ve
  tekrarları tek ayrımda kalır. Gerçek kod dağılımı eğitimden önce dondurulur.
  Ortak 100 cümle nedeniyle metin örtüşmesi vardır; bu küme yeni konuşmacıya
  genellemeyi değerlendirir. Görülmemiş ifade testi ayrıca hazırlanmalıdır.
- Baseline ve fine-tuned değerlendirmesi aynı dondurulmuş testle yapılır;
  test sesi/transkripti eğitim veya parametre seçimi için kullanılmaz.
- Gerçek sesler `datasets/audio/`, gerçek manifestler
  `datasets/manifests/asr_train_real.jsonl`, `asr_val_real.jsonl`,
  `asr_test_real.jsonl` gibi gitignore kapsamındaki yerel yollarda kalır.
  İmzalı form ve eşleme depo dışında tutulur; dosyalar veya yedekler herkese
  açık ortama aktarılmaz. Yalnızca erişimi kısıtlı yerel yedek kullanılır.
- Toplama sonrası bütün manifestler birlikte kontrol edilir:
  `uv run python experiments/asr/validate_manifest.py datasets/manifests/asr_train_real.jsonl datasets/manifests/asr_val_real.jsonl datasets/manifests/asr_test_real.jsonl --check-files`.
  Bu komut şema, kimlik, dosya ve konuşmacı sızıntısını kontrol eder; ses kalitesini,
  gerçek izni veya transkript doğruluğunu kanıtlamaz. Bu oturumda çalıştırılmadı;
  gerçek manifestler oluşturulmadı.
- Bulut varsayılan kapalıdır; ayrı açık izin ve ekip kararı olmadan aktarım yoktur.
  Geri çekilmede ses/transkript/manifest/yedek ve etkilenmiş model kopyaları
  formdaki plana göre ele alınır. Teslim + 3 ay sınırında ham veriler, bireysel
  transkriptler, kod eşlemeleri ve izin belgeleri silinir; yalnızca toplu metrikler
  kalır. Silme takibi kimlik içermeyen işlem kaydıyla belgelenir.

## Kayıt aracı (`voxflow record` / `voxflow verify`)

Kurulum: `uv sync --extra dev --extra audio`. Araç model indirmez, ASR çalıştırmaz.

```bash
uv run --extra audio voxflow record \
  --speaker spk_01 --session s01 --split train \
  --consent team_consent_v1 --environment quiet \
  --device-note "dahili mikrofon" --limit 25
```
- Cümleleri `docs/recording_sentences_tr.md` dosyasından sırayla gösterir; Enter ile kaydeder,
  Enter ile bitirir. `t` aynı cümleyi yeniden alır, `a` atlar, `ç` oturumu bitirir.
- Ses `datasets/audio/<spk>/` altına **16 kHz mono PCM-16 WAV** olarak yazılır (git dışı).
- Her kayıt için ASR manifestine (`datasets/manifests/asr_<spk>_real.jsonl`, git dışı) şemadaki
  **10 alan** yazılır. Cümle kimliği, tekrar numarası, ortam, cihaz ve kontrol durumu
  manifeste değil, protokolün istediği gibi ayrı yerel çizelgeye
  (`datasets/audio/<spk>/session_<id>.csv`) yazılır.
- `--consent` zorunludur ve boş bırakılamaz; açık izin alınmadan kayıt başlamaz. Alanın dolu
  olması tek başına izin kanıtı değildir (bkz. `docs/consent_form_tr.md`).
- `quality_flags` otomatik: kırpılma oranı > %0.1 ise `clipping`, `--environment noisy` ise
  `noise`, aksi hâlde `ok`. `ok` başka bayrakla birlikte yazılmaz.
- Oturum kaldığı yerden devam eder: manifestte kaydı olan cümleler atlanır.
- Çok kısa (< 0.3 sn) ve sessiz kayıtlar hata verir, dosyaya yazılmaz.

Doğrulama turu (insan kontrolü — transkript, listenin kopyası değil gerçekten söylenendir):
```bash
uv run --extra audio voxflow verify --manifest datasets/manifests/asr_spk_01_real.jsonl
```
Her kaydı çalar, hedef metni gösterir: `Enter` doğru, `d` düzelt (gerçekten söyleneni yaz),
`r` reddet (manifestten çıkarır ve sesi siler), `ç` çık. Onaylananlar çizelgede
`verified=yes` olarak işaretlenir. Ses çalma yoksa `--no-audio` ile metin üzerinden yürütülür.

Toplama sonrası tüm manifestler birlikte denetlenir (şema, kimlik, dosya, konuşmacı sızıntısı):
`uv run python experiments/asr/validate_manifest.py datasets/manifests/asr_*_real.jsonl --check-files`
