# Deney: Kural tabanlı / Qwen / Hibrit karşılaştırması — nlu_dev_v1

| Alan | Değer |
|---|---|
| Tarih | 2026-11-25 |
| Koşan | Melike Nesrin Zaman |
| İzlek | NLU (hiçbir model eğitilmedi; hazır modeller) |
| Veri | `datasets/manifests/nlu_dev_v1.jsonl` (n = 66, dondurulmuş) |
| Betik | `experiments/nlu/eval_rule_based.py`, `REFERENCE_TODAY=2026-10-19` |
| Modeller | Ollama üzerinden `qwen2.5:3b`, `qwen2.5:1.5b` (q4) |
| Donanım | Linux, i7 11. nesil; LLM çıkarımı CPU |

## Sonuçlar

| Yapılandırma | Niyet doğruluğu | Makro F1 | Slot tam eşleşme | LLM çağrısı | Geçerli LLM yanıtı | Ortalama gecikme |
|---|---|---|---|---|---|---|
| Kural tabanlı | **1,000** | **1,000** | **1,000** | 0 / 66 | — | **0,11 ms** |
| Qwen2.5 3B | 0,803 | 0,801 | 0,576 | 66 / 66 | 0,985 | 6 434 ms |
| Qwen2.5 1.5B | 0,727 | 0,622 | 0,470 | 66 / 66 | 0,864 | 2 491 ms |
| Hibrit (kural + 3B) | 0,985 | 0,974 | 0,985 | 4 / 66 | 1,000 | 473 ms |

"Geçerli LLM yanıtı", modelin ürettiği çıktının şemadan ve izin listesinden geçip
kullanılabildiği oranı gösterir; geçersiz JSON, katalog dışı niyet, şema hatası ve
bağlantı hatası bu oranın dışında kalır ve kurallı yorumlayıcıya düşülür.

## Bulgular

### 1. Kurallı yorumlayıcı bu kümede hatasız, ancak sonuç bağımsız değil
Kural tabanlı çözümleyici 66/66 doğru sonuç vermektedir. Bu değer dikkatle okunmalıdır:
kümedeki beş hata, #21 kapsamında kuralları düzeltmek için kullanılmıştır. Dolayısıyla
`nlu_dev_v1` artık kurallı sistem için **bağımsız bir test kümesi değil, geliştirme
kümesidir**. Kuralların genelleme başarımı ancak hiç görülmemiş yeni bir küme üzerinde
ölçülebilir.

### 2. Dil modelleri katalog dışına çıkmakta, doğrulama bunu engellemektedir
`qwen2.5:1.5b`, tanımlı on iki niyetin dışında `edit_note`, `close_app`, `weather`,
`play_music`, `send_message`, `show_time` ve `execute_command` gibi niyetler üretmiştir.
Bu çıktılar doğrulama katmanında reddedilmiş ve kurallı çözümleyiciye düşülmüştür;
hiçbiri işlem başlatmamıştır. Geçerli yanıt oranının 1.5B'de 0,864'e düşmesi büyük ölçüde
bu nedenledir. Güvenlik tasarımının beklendiği gibi çalıştığı, ölçümle gösterilmiştir.

### 3. Dil modelinin asıl zayıflığı parametre çıkarımıdır
Niyet doğruluğu 0,803 iken slot tam eşleşmesi 0,576'ya düşmektedir. Tipik hatalar:
- `görev ekle` için var olmayan bir başlık uydurulması (`"Ödev 1"`)
- Başlığın metinden çıkarılması yerine yeniden yazılması (`sunum hazırla` → `Günkü Sunum Hazırlama`)
- Tarih ifadesinin atlanması (`yarın için matematik ödevi` → tarih yok)

Bunlardan birincisi sistem açısından en risklisidir: kural tabanlı çözümleyici başlık
olmadığında kullanıcıya soru sorarken, dil modeli uydurduğu başlıkla doğrudan kayıt
oluşturulmasına yol açabilir.

### 4. Gecikmeyi model boyutu değil istem tasarımı belirlemektedir
Aynı model (`qwen2.5:3b`) bu ölçümde örnek başına 6,4 saniye sürerken, 1 Kasım'daki kısa
istemli ve çıktı uzunluğu sınırlı ölçümde 0,20 saniyede yanıt vermişti. Aradaki fark
uyarlayıcının uzun sistem istemi ve çıktı uzunluğunun sınırlanmamış olmasıdır. Hibrit
yapıda ortalama gecikmenin 473 ms'ye inmesinin nedeni, çağrıların yalnızca 66 örnekten
4'ünde yapılmasıdır.

### 5. Hibrit yönlendirmede tasarım kusuru bulunmuştur
Hibrit yapı 0,985 ile kurallı çözümleyicinin (1,000) altında kalmıştır. Nedeni şudur:
yönlendirme kuralı "kural `unknown` derse dil modeline sor" biçimindedir; oysa `unknown`
bir başarısızlık işareti değil, **geçerli bir yanıttır**. Kurallı çözümleyici beş örnekte
doğru olarak `unknown` demiş, bunlardan dördü dil modeline gönderilmiş ve model `evet`
ifadesini (bekleyen onay yokken) `affirm` olarak yorumlamıştır.

Bu hatanın sistem üzerindeki etkisi ayrıca sınanmıştır: diyalog yöneticisi, bekleyen onay
bulunmadığında `affirm` niyetini kabul etmemekte, kullanıcıya "onaylanacak bekleyen bir
işlem yok" yanıtını vermekte ve **hiçbir komut üretmemektedir**. Dolayısıyla hata niyet
katmanında görülmekte, işlem katmanına yansımamaktadır. Bu durum, niyet doğruluğu ile
işlem başarı oranının ayrı ölçülmesinin gerekçesini bir kez daha göstermektedir.

## Öneriler

1. Hibrit yönlendirme ölçütü daraltılmalıdır: `unknown` tek başına dil modeline geçiş
   gerekçesi sayılmamalı; kısa onay/ret ifadeleri ve anlamsız girdiler kuralda
   bırakılmalıdır.
2. Uyarlayıcıda çıktı uzunluğu sınırlanmalı ve sistem istemi kısaltılmalıdır; gecikmenin
   ana kaynağı budur.
3. Kuralların genelleme başarımı için, düzeltmelerde kullanılmamış yeni bir test kümesi
   hazırlanmalıdır.
4. Varsayılan model seçiminde `qwen2.5:3b`'nin araştırma lisansı altında olduğu göz
   önünde bulundurulmalıdır; kısıtsız kullanım gerektiğinde Apache 2.0 lisanslı 1.5B veya
   7B sürümleri tercih edilmelidir.

## Sınırlılıklar
Tek küme (n = 66), tek donanım, tek koşu. Dil modeli çıktıları örnekleme sıcaklığı sıfır
olmasına karşın tam olarak yinelenebilir değildir. Gecikme değerleri işlemci üzerinde
ölçülmüştür; GPU üzerinde daha düşük beklenir. Küçük örneklemde oranlar kesinlik iddiası
taşımaz.
