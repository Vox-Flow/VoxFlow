#!/usr/bin/env bash
# docs/team_tasks.md içindeki Faz 2-5 işlerini GitHub issue olarak açar.
# Kullanım: gh auth login yapıldıktan sonra  ./scripts/create_issues.sh <owner/repo>
set -euo pipefail
REPO="${1:?owner/repo gerekli}"

for l in "faz-2" "faz-3" "faz-4" "faz-5" "asr" "nlu" "cli" "storage" "docs" "test" "hoca-karari-bekliyor" "bug" "task"; do
  gh label create "$l" --repo "$REPO" --force >/dev/null 2>&1 || true
done

mk() { gh issue create --repo "$REPO" --title "$1" --label "$2" --body "$3" >/dev/null && echo "✓ $1"; }

mk "[#7] SounddeviceCapture gerçek mikrofon doğrulaması" "faz-2,asr,task" \
"Sorumlu: İremsu / Destek: Melike
Kabul: 16 kHz mono; boş/sessiz kayıt hata verir; cihaz yoksa anlaşılır mesaj; üç OS'te manuel tablo doldurulur (docs/testing.md)."
mk "[#8] faster-whisper model seçimi (tiny/base) ve çevrimdışı yükleme" "faz-2,asr,task,hoca-karari-bekliyor" \
"Sorumlu: İremsu / Destek: Helin
Kabul: 'voxflow info' ASR hazır; uçak modunda transkript; gecikme/bellek ölçümü experiments/asr/. İndirme ekip kararıyla."
mk "[#9] Referans kayıtları (açık izinli, anonim ID) + ASR manifesti" "faz-2,asr,task" \
"Sorumlu: İremsu / Destek: Melike
Kabul: manifest şemaya uyar (docs/dataset_protocol.md); transkriptler insan kontrollü; ses dosyaları git dışı."
mk "[#10] WER/CER baseline betiği gerçek veriyle" "faz-2,asr,test,task" \
"Sorumlu: İremsu / Destek: Melike
Kabul: experiments/asr/eval_wer.py gerçek manifestte çalışır; rapor experiments/reports/ şablonuyla."
mk "[#11] OllamaInterpreter (qwen2.5, JSON mod, sıkı doğrulama, fallback)" "faz-3,nlu,task" \
"Sorumlu: Helin / Destek: Melike
Kabul: sunucu yokken CLI çökmez; şema dışı çıktı reddedilir; birim test HTTP mock ile."
mk "[#12] 50+ Türkçe komut NLU manifesti" "faz-3,nlu,docs,task" \
"Sorumlu: Melike / Destek: Helin, İremsu
Kabul: ≥5 örnek/niyet; ≥10 unsupported/unknown; varyant sızıntısı yok; split dondurulur."
mk "[#13] Kural vs Qwen karşılaştırma betiği" "faz-3,nlu,test,task" \
"Sorumlu: Melike / Destek: Helin
Kabul: aynı test kümesi; intent acc, macro-F1, slot EM, geçerli JSON oranı, gecikme; rapor tablo."
mk "[#14a] ASR izleği: Whisper fine-tune konfig iskeleti + smoke test" "faz-4,asr,task,hoca-karari-bekliyor" \
"Sorumlu: İremsu. Yalnızca hoca ASR derse. Sentetik 3 örnekle smoke test; gerçek eğitim ekip onayıyla."
mk "[#14b] NLU izleği: Qwen2.5 0.5B/1.5B QLoRA konfig iskeleti + smoke test" "faz-4,nlu,task,hoca-karari-bekliyor" \
"Sorumlu: Helin. Yalnızca hoca NLU derse. 4 GB VRAM sınırı; gerçek eğitim ekip onayıyla."
mk "[#15] Deney kayıt disiplini: her çalışma TEMPLATE.md ile" "faz-4,docs,task" \
"Sorumlu: Melike. experiments/reports/TEMPLATE.md kullanımı; config/seed/model/veri sürümü zorunlu."
mk "[#16] 50 komutluk uçtan uca değerlendirme (intent acc ve işlem başarı oranı ayrı)" "faz-5,test,task" \
"Sorumlu: Melike. Gerçek veri olmadan sonuç yazılmaz."
mk "[#17] Windows/macOS manuel kontrol listesi ve gerçek test kaydı" "faz-5,cli,test,task" \
"Sorumlu: Helin. docs/testing.md platform tablosu doldurulur."
mk "[#18] README/docs güncelleme, izlenebilirlik matrisi" "faz-5,docs,task" \
"Sorumlu: Melike."
mk "[altyapı] CODEOWNERS GitHub kullanıcı adlarını güncelle, branch protection kur" "docs,task" \
"Sorumlu: Melike. main ve develop: PR zorunlu, 1 onay, CI geçmeli, force-push kapalı. Kanban: Backlog→Bu Sprint→Devam Ediyor→Review→Done."
