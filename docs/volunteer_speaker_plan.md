# Gönüllü Konuşmacı Planı — #17 taslağı

**Durum:** Katılımcı aranmadı, izin alınmadı, kayıt yapılmadı; aşağıdakiler boş
plan kontenjanlarıdır. İsim, iletişim, demografi veya ekip onayı temsil etmez.
Sorumlu rol: İremsu (ses/ASR); destek rol: Melike (veri/kalite), mevcut görev dağılımına göre.
Görev tablosundaki 14c, GitHub #17 kapsamıyla eşleştirilir; tablodaki yerel 17
numarası bu işin issue numarası değildir.

## Hedef ve dağılım

| Plan kodu | Ayrım | Cümle hedefi | Katılım / izin / kayıt |
|---|---|---:|---|
| spk_01 | train | 100 | Bekliyor / yok / yok |
| spk_02 | train | 100 | Bekliyor / yok / yok |
| spk_03 | train | 100 | Bekliyor / yok / yok |
| spk_04 | train | 100 | Bekliyor / yok / yok |
| spk_05 | train | 100 | Bekliyor / yok / yok |
| spk_06 | val | 100 | Bekliyor / yok / yok |
| spk_07 | test | 100 | Bekliyor / yok / yok |
| spk_08 | test | 100 | Bekliyor / yok / yok |

En az 8 farklı yetişkin gönüllü, 800 kabul edilmiş kayıt hedeflenir; tamamlanmış
sayı değildir. Ortalama 3 saniye varsayımıyla 40 dakika net ses eder; 10 konuşmacı
900–1000 kayıtla yaklaşık 45–50 dakika sağlar. ADR-008'deki yaklaşık bir saat
hedefine ulaşıldığı iddia edilmez. Ek kontenjanlar önce train için önerilir;
nihai dağılım gerçek katılımcılar belli olunca, eğitim öncesi dondurulur.

## Davet ve oturum sırası

1. Sorumlu rol, ekip incelemesinden sonra gönüllülük ve vazgeçme hakkını açıklayan
   daveti yetişkin gönüllülere iletir. Bu belge davetin gönderildiği anlamına gelmez.
2. Katılımcının tercihine göre farklı konuşma biçimleri ve kayıt cihazları için
   çeşitlilik aranır; aksan taklidi istenmez, hassas demografi toplanmaz. Temsiliyet
   veya yaş/cinsiyet dengesi sağlandı diye raporlanmaz.
3. Boş izin formundaki iletişim ve son silme tarihi doldurulur; açıklama yapılır,
   açık izin alınır, kod atanır. Ad ve iletişim yalnızca ayrı yerel izin alanında kalır.
4. Kişi başına 15–25 dakika, 25 cümlede bir mola planlanır. Oturum zamanı ve cihaz
   ancak gönüllüyle anlaşıldıktan sonra yerel çizelgeye eklenir.
5. Kayıt sorumlusu kaliteyi, destekçi transkripti kontrol eder; gerçek kontrol
   yapıldığında yerel takip kaydı tutulur. Onaysız veya eksik kayıt hedefe sayılmaz.

Bir kişi vazgeçerse kodu yeniden kullanılmaz; yeni gönüllü yeni kodla aynı ayrım
kontenjanını doldurur. Sekiz kişiye ulaşılamazsa hedef eksik olarak raporlanır;
aynı kişinin farklı oturumları yeni konuşmacı sayılmaz. Test konuşmacıları train
veya val içine alınmaz. Bulut izni vermeyen kişi yerel plana katılabilir.

## Açık bağımlılık

[PR #20](https://github.com/Vox-Flow/VoxFlow/pull/20) için belirtilen eksik
kaynak bu çalışma kopyasında yok; 2026-11-01 GitHub API okuması 404 döndürdü.
Kaynağın adı, içeriği ve PR kabul koşulları doğrulanamadı. Kaynağa dayalı cümle
kapsaması ve protokol uyumluluğu doğrulaması **bekliyor**. Bu belgeler bağımsız
proje belgelerine dayanır; PR #20 gereksinimlerinin karşılandığı iddia edilmez.
Kaynak erişilebilir olduğunda İremsu rolü liste/protokol eşlemesini, Melike rolü
kontrolünü yapmalı; gerçek görevlendirme ve ekip onayı henüz alınmış değildir.
