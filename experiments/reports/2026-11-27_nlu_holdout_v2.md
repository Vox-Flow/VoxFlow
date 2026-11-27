# Deney: Kurallı NLU'nun bağımsız test kümesindeki başarımı (nlu_test_v2)

| Alan | Değer |
|---|---|
| Tarih | 2026-11-27 |
| Koşan | Melike |
| İzlek | NLU |
| Model + sürüm | rule_based (LLM yok) |
| Veri manifesti + sürüm | datasets/manifests/nlu_test_v2.jsonl @ dad0f85 |
| Split | test (n = 36), **tutulmuş küme** |
| Config | yok (kural tabanlı) |
| Seed | yok (deterministik) |
| Donanım | Linux x86_64, CPU; model çalıştırılmadı |

## Neden bu ölçüm yapıldı

`nlu_dev_v1` üzerinde raporladığımız **1,000** değeri genelleme başarımı değildir: o kümedeki
beş hata #21'de kuralları düzeltmek için kullanıldı, yani küme **geliştirme kümesine** dönüştü
(#35). Bu deney, düzeltmelerde hiç kullanılmamış 36 örneklik yeni bir kümeyle gerçek başarımı
ölçer. Küme yazılırken mevcut kural anahtar sözcüklerine bakılmadı; doğal söyleyişler yazıldı.

## Metrikler

| Metrik | nlu_dev_v1 (geliştirme) | **nlu_test_v2 (tutulmuş)** |
|---|---|---|
| Niyet doğruluğu | 1,000 | **0,722** |
| Makro-F1 | 1,000 | **0,720** |
| Slot tam eşleşme | 1,000 | **0,694** |
| Ortalama gecikme | ~0,2 ms | 0,19 ms |

**Aradaki 0,278'lik fark, kuralların kendi geliştirme kümesine aşırı uyumudur.**
Rapora yazılacak sayı 0,722'dir; 1,000 yalnızca "geliştirme kümesi" etiketiyle anılabilir.

## Gözlemler — 11 hatanın dağılımı

Hatalar rastgele değil, **dört öbekte** toplanıyor:

1. **Eş anlamlı fiil eksikliği (5 hata).** Kurallar fiil köklerinin dar bir listesini tanıyor.
   - `komut geçmişini sıfırla` → unknown (`sil`/`temizle` var, `sıfırla` yok)
   - `geçmiş kayıtlarını sil` → unknown (araya giren `kayıtlarını` kalıbı bozuyor)
   - `şunu not et: oda numarası 312` → unknown (`not al/ekle/tut` var, `not et` yok)
   - `bir şey not alabilir misin` → unknown (kibar soru kalıbı)
   - `neler yapmam gerekiyor` → unknown (anahtar sözcük `görev` geçmiyor)

2. **Desteklenmeyen istekler `unknown`'a düşüyor (3 hata).** `alarm kur`, `ışıkları kapat`,
   `ekran görüntüsü al` → unsupported yerine unknown. Kullanıcıya "anlamadım" yerine
   "bunu yapamıyorum" demek gerekirdi; davranış farkı kullanıcı deneyimidir, güvenlik değil.

3. **Niyet çakışması (1 hata).** `görev listemi aç` → open_app. `aç` fiili uygulama açma
   kuralını tetikliyor, `görev` sözcüğünü geçersiz kılıyor. **Bu en riskli hata:**
   yanlış niyet sessizce yanlış eyleme gidiyor.

4. **Bağlam gözden kaçıyor (1 hata).** Bekleyen `create_task.title` varken `gerek yok` →
   cancel yerine create_task; yani "gerek yok" görev başlığı sanılıyor. İptal sözcük listesi
   (`vazgeçtim`, `iptal`, `boşver`) dar.

5. **Slot sınırı taşması (1 hata).** `bu akşam için spor salonu görevi ekle` → başlık
   `bu akşam spor salonu` çıkıyor; tarih ifadesi başlıktan ayrılmıyor. Niyet doğru,
   slot yanlış — eylem yanlış başlıkla oluşur.

### Sınırlılıklar
- n = 36, küçük örneklem; %95 güven aralığı geniş (kabaca ±0,15).
- Örnekler ekipçe yazıldı, gerçek kullanıcı dağılımı değil; ASR çıktısı da içermiyor.
- Hibrit (Ollama) sağlayıcı bu makinede ölçülemedi — Ollama kurulu değil. Aynı küme
  GPU'lu makinede `--provider hybrid` ile tekrar koşulmalı.

## Sonuç ve sonraki adım

Küme bundan sonra **dondurulmuştur**: bu 11 hataya bakarak kural yazmak, v2'yi de geliştirme
kümesine çevirir ve ölçümü yine geçersiz kılar. Yapılacak doğru iş:

1. Kural iyileştirmeleri **`nlu_dev_v1` üzerinde** yapılır (orası zaten geliştirme kümesi).
2. v2 yalnızca son ölçümde, tek seferde koşulur.
3. Yeni düzeltmeler gerekirse v3 yazılır.
4. Aynı küme hibrit sağlayıcıyla da ölçülüp iki sayı raporda yan yana verilir — hibritin
   asıl değeri muhtemelen burada, 1. ve 2. öbekteki eş anlamlı/kapsam dışı ifadelerde görünecek.

Rapordaki dürüst cümle şudur: *kurallı çözümleyici geliştirme kümesinde 1,000, bağımsız
tutulmuş kümede 0,722 niyet doğruluğu vermiştir; aradaki fark kural tabanlı yaklaşımın
genelleme sınırını gösterir.*
