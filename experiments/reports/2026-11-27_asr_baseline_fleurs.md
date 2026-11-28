# Deney: Uyarlama öncesi ASR taban ölçümü (FLEURS Türkçe)

| Alan | Değer |
|---|---|
| Tarih | 2026-11-27 |
| Koşan | Melike |
| İzlek | ASR |
| Model + sürüm | faster-whisper `base` ve `small`, int8, CPU |
| Veri manifesti + sürüm | `datasets/manifests/asr_test_real.jsonl` @ a75047b |
| Split | test (n = 743), **dondurulmuş**, 2,61 saat |
| Config | yok (hazır model, uyarlama öncesi) |
| Seed | yok (greedy/beam=5, deterministik) |
| Donanım | Linux x86_64, 16 çekirdek, RAM 15,4 GiB. **GPU kullanılmadı** — cuBLAS 12 kurulu değil, çalışma zamanı CPU/int8'e düşüyor |

## Amaç

Uyarlamanın (#8) karşılaştırılacağı referans noktası. Aynı betik, aynı normalizasyon
ve **aynı dondurulmuş test kümesi** uyarlama sonrası tekrar koşulacak.

## Metrikler

| Model | WER | CER | Ortalama gecikme | Örnek başına gerçek zaman oranı |
|---|---|---|---|---|
| `base` | **0,2572** | 0,0673 | 0,672 sn | ~19× hızlı |
| `small` | **0,1350** | 0,0339 | 2,019 sn | ~6× hızlı |

Normalizasyon her iki tarafa da uygulanır: `services/text_utils.normalize`
(Türkçe İ/I farkı, noktalama ve fazla boşluk temizliği). Yani noktalama ve
büyük/küçük harf farkı WER'e yansımaz.

## Gözlemler

**`small`, `base`'in yarısından az hata yapıyor** (0,135'e karşı 0,257) ve bu fark
yayımlanmış Türkçe sonuçlarıyla uyumlu — literatürde Whisper small Türkçe için ~%18 WER
bildiriliyor, bizim 13,5'imiz FLEURS'ün temiz stüdyo kaydı ve okunmuş metin olmasıyla
açıklanabilir. **Bu, veri hattının doğru çalıştığının da kanıtıdır:** metin–ses hizası
bozuk olsaydı WER 1,0'a yakın çıkardı.

Tipik hatalar kısaltma ve özel adlarda yoğunlaşıyor:

| Referans | `base` hipotezi |
|---|---|
| USOC'nin; lisans iptali… | US OSY'nin lisan siptali… |
| …değişiklikler yapmaya… | …değişikler yapmaya… |

CER'in WER'den çok düşük olması (0,067 / 0,257) hataların **kelime sınırı ve ek**
düzeyinde olduğunu, tamamen yanlış çözümleme olmadığını gösteriyor — Türkçenin
eklemeli yapısında beklenen bir örüntü.

### Sınırlılıklar

- **Alan uyuşmazlığı:** FLEURS haber/ansiklopedi cümleleri, ortalama 12,6 saniye ve
  17 kelime. VoxFlow'un alanı 1–3 saniyelik kısa komutlar. Bu sayılar **ürünün gerçek
  kullanım başarımı değildir**, uyarlama için referanstır.
- **GPU ölçülmedi.** Gecikme sayıları CPU'ya aittir; gerçek kullanımda GPU ile düşer.
- `initial_prompt` kullanılmadı. CLI gerçek kullanımda alan sözlüğü ipucu veriyor;
  bu ölçüm onsuz yapıldı (artık `--initial-prompt` bayrağı var).
- Konuşmacı-ayrıklık **veriden doğrulanamadı** (FLEURS kimlik yayımlamıyor); cümle
  ayrıklığı doğrulandı: train∩test = 0, train∩dev = 0, dev∩test = 0.

## Sonuç ve sonraki adım

Taban kaydedildi. Uyarlama sonrası ölçüm **aynı test kümesinde, aynı betikle** yapılacak
ve sonuç iyileşsin ya da iyileşmesin raporlanacak (#63, Helin).

Uyarlamanın `base` üzerinde yapılması planlanıyor; `small`'un tabanı da buraya
kaydedildi ki "zaten small kullansaydık" sorusuna sayıyla cevap verebilelim.
