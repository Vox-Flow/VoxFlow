# Ekip Toplantısı — Sprint 1 ara değerlendirme

**Tarih:** ____ Kasım 2026   **Katılan:** Helin, İremsu, Melike   **Süre hedefi:** 30 dk
Kanban: https://github.com/orgs/Vox-Flow/projects/3

## 1. Durum turu (her kişi 3 dk: bitti / takıldım / sırada)
| Kişi | Bitti | Takıldığı yer | Sırada |
|---|---|---|---|
| İremsu | #24 izin formu/protokol (merge) | | #1 mikrofon, #2 Whisper base, Ollama kıyası |
| Helin | #26 kural düzeltmeleri, #27 Ollama adaptörü (review'da) | format + httpx + is_available | düzeltme, merge, gerçek Ollama ölçümü |
| Melike | #20 manifest, #22 kıyas, #23 docs, #25 e2e (merge) | | Linux mikrofon denemesi, rapor iskeleti |

## 2. Karar gerektiren maddeler
| # | Karar | Seçenekler | Karar / sahibi |
|---|---|---|---|
| K1 | Depo görünürlüğü | public (branch protection açılır, portfolyo) / private (koruma yalnızca disiplin) | |
| K2 | İzin formu iletişim kanalı (silme talebi) | ekip e-postası / tek kişi / form | |
| K3 | Son silme tarihi | teslim + 3 ay = ____ | |
| K4 | NLU varsayılan modeli | qwen2.5:3b (ölçüldü) / İremsu+Helin ölçümünden sonra | |
| K5 | Whisper base indirme onayı (İremsu, kendi makinesi) | evet / hayır | |
| K6 | Sprint 1 bitiş + Sprint 2 toplantı günü | ____ / ____ | |
| K7 | Kayıt cümle listesi: İremsu'nun C001–C100 mü, nlu_dev_v1 mi, birleşim mi | | |

## 3. Riskler
- Veri toplama en uzun iş; gönüllü bulma ve izin süreci bu hafta başlamazsa Faz 4 kayar.
- Helin'in review yükü: her PR'ı o okuyorsa darboğaz. Öneri: Melike↔İremsu çapraz review, Helin yalnızca NLU/entegrasyon.
- Whisper fine-tune kazancı küçük çıkabilir (ADR-008 riski); raporda "domain adaptation" çerçevesi önceden kabul edilsin.

## 4. Aksiyonlar (toplantıda doldurulur)
| Aksiyon | Sahip | Tarih |
|---|---|---|
| | | |

## 5. Notlar
