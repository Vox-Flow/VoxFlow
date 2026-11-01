# Değerlendirme Protokolü (uçtan uca)

Amaç: "sesli komut → doğru işlem" başarısını **üç ayrı katmanda** ölçmek, böylece hatanın nereden geldiği (ASR mı, NLU mu, diyalog mu) görünsün. Tek bir yüzdeyle "başarı" iddia edilmez.

## Katmanlar ve metrikler
| Katman | Girdi → Çıktı | Metrik | Betik |
|---|---|---|---|
| ASR | ses → metin | WER, CER, gecikme | `experiments/asr/eval_wer.py` |
| NLU | metin → niyet+slot | intent accuracy, macro-F1, slot exact match, geçerli JSON oranı (LLM), gecikme | `experiments/nlu/eval_rule_based.py`, `bench_ollama_quick.py` |
| İşlem | niyet+slot+diyalog → gerçek fonksiyon çağrısı | **işlem başarı oranı**: beklenen handler, beklenen parametrelerle çağrıldı mı (mock launcher/store) | `experiments/e2e/eval_pipeline.py` |

İşlem başarı oranı ≠ görev "tamamlandı" durumu. Birincisi sistemin doğru eylemi seçmesi, ikincisi kullanıcının görevini bitirmesidir; ikincisi ölçülmez.

## Veri
- Metin kümesi: `datasets/manifests/nlu_dev_v1.jsonl` (66, dondurulmuş). Her satırda beklenen niyet, slot ve bağlam var.
- Ses kümesi: `datasets/manifests/asr_test.jsonl` (git dışı), konuşmacı-ayrık. Her ses kaydı bir metin örneğine `nlu_ref_id` ile bağlanır; böylece aynı cümle hem ASR hem NLU hem işlem katmanında ölçülür.
- Beklenen işlem, niyetten türetilir: create_task → `store.add_task(title, date)`, open_app → `launcher.open_app(key)`, clear_history → onay turu + `store.clear_history()`, unsupported/unknown → **hiçbir** fonksiyon çağrılmaz, cancel → bekleyen işlem temizlenir.

## İki koşu modu
1. **Referans metinle** (ASR'siz üst sınır): manifestteki `utterance` doğrudan NLU'ya verilir. Şimdi koşulabilir.
2. **ASR çıktısıyla**: ses → Whisper → metin → NLU → işlem. Ses kümesi hazır olunca.
   İkisinin farkı = ASR hatalarının işlem başarısına maliyeti. Baseline Whisper ve fine-tuned Whisper aynı ses kümesinde, aynı NLU ile karşılaştırılır.

## Raporlama kuralları
- Her koşu `experiments/reports/TEMPLATE.md` ile: tarih, kim, model/veri sürümü (commit), config hash, metrikler, en az 3 hata örneği.
- n küçükken (≤100) yüzdeler ±5 puan belirsiz kabul edilir; "istatistiksel olarak anlamlı" denmez.
- Hedef (%90 doğru işlem seçimi, temiz ses) **hedef** olarak yazılır; ölçülen değer ayrı sütunda.
- Platform: hangi OS'te koşulduğu yazılır; CI yalnızca metin modunu üç OS'te koşar.
