# Katkı Rehberi

Üç kişilik ekip, üç farklı işletim sistemi. Bu belge kısa tutulmuştur; kural değil, ortak alışkanlıktır.

## 1. Kurulum

Ön koşul: Python ≥ 3.11 ve [uv](https://docs.astral.sh/uv/).

**Linux / macOS**
```bash
git clone https://github.com/Vox-Flow/VoxFlow.git && cd VoxFlow
uv sync --extra dev
uv run voxflow --text "görevleri listele"
uv run pytest
```

**Windows (PowerShell)**
```powershell
git clone https://github.com/Vox-Flow/VoxFlow.git; cd VoxFlow
uv sync --extra dev
uv run voxflow --text "görevleri listele"
uv run pytest
```

Kişisel ayarlar: `config/app.example.json`, `apps.example.json`, `sites.example.json` dosyalarını `.example` olmadan kopyalayın ve kendi OS'inize göre düzenleyin. Bu kopyalar git'e girmez.

Ses/ASR (isteğe bağlı, ekip kararıyla): `uv sync --extra dev --extra audio --extra asr`.

## 2. Dal (branch) modeli

```
feat/asr-faster-whisper ──PR──▶ develop ──PR (faz teslimi, vX.Y.0 tag)──▶ main
```
- `main`: her zaman hocaya gösterilebilir. Yalnızca `develop`'tan PR alır.
- `develop`: entegrasyon dalı. Yalnızca PR alır; doğrudan push yok.
- İş dalları: `feat/…`, `fix/…`, `docs/…`, `test/…`, `exp/…` (deneyler). Kısa, küçük harf, tire ile.
- Dal `develop`'tan açılır, iş bitince `develop`'a PR edilir. Dallar merge sonrası **silinmez** (geçmiş izlenebilir kalsın).

## 3. Commit mesajı (Conventional Commits)

```
feat(nlu): Ollama Qwen adaptörü eklendi
fix(dates): "haftaya pazartesi" yanlış güne çözülüyordu
test(storage): bozuk JSON senaryosu
docs(setup): Windows kurulum adımları
exp(asr): tiny vs base WER karşılaştırması
```
Tipler: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`, `exp`. Kapsam parantez içinde modül adı.

## 4. Pull Request kuralları

- Claude Code kullanıyorsanız commit/PR'lara otomatik "Co-Authored-By: Claude" eklenmesini kapatın: `~/.claude/settings.json` → `"attribution": {"commit": "", "pr": ""}`. Yazar her zaman gerçek ekip üyesidir.

- Küçük PR: ideal < 300 satır. Büyükse böl.
- Şablonu doldur: ne / neden / nasıl test edildi / hangi OS'te denendi.
- **En az 1 onay** (CODEOWNERS otomatik atar) ve **CI yeşil** olmadan merge yok.
- Yazar kendi PR'ını merge edebilir, onay geldikten sonra. "Squash and merge" tercih edilir.
- 24 saat içinde review gelmezse yazar merge edebilir; bir sonraki toplantıda söyler.
- Hoca kararına bağlı işler (model indirme, eğitim) PR'dan önce ekip kararı ister; issue'da `hoca-karari-bekliyor` etiketi kalkmış olmalı.

## 5. PR açmadan önce yerelde

```bash
uv run ruff format src tests experiments
uv run ruff check src tests experiments
uv run pytest
```
İsteğe bağlı: `uv run pre-commit install` ile bunlar her commit'te otomatik çalışır.

## 6. Test ve platform

- Yeni davranış = yeni test. `tests/unit` (tek modül) ve `tests/integration` (uçtan uca metin akışı).
- Testler model, mikrofon veya internet **gerektirmez**. Gerektiren şey varsa `@pytest.mark.skipif` ile atlanır ve nedeni yazılır.
- Mikrofon/uygulama açma gibi CI'da denenemeyen şeyler `docs/testing.md` platform tablosuna "kim, hangi OS, tarih" ile yazılır.

## 7. Gizlilik ve güvenlik

- Asla commit etme: `config/*.json` (example hariç), `history.json`, `*.wav` ve diğer sesler, `datasets/audio/`, `*_real*.jsonl`, model dosyaları.
- Ses kaydı toplanacaksa açık izin formu ve anonim `speaker_id`; bkz. `docs/dataset_protocol.md`.
- LLM çıktısı komut değildir; yalnızca `Intent` seçer. `shell=True`, `eval`, serbest URL yok.

## 8. Issue ve kanban

GitHub Projects sütunları: `Backlog → Bu Sprint → Devam Ediyor → Review → Done`. Her iş bir issue; şablon `.github/ISSUE_TEMPLATE/`. Etiketler: `faz-2`…`faz-5`, `asr`, `nlu`, `cli`, `storage`, `docs`, `test`, `hoca-karari-bekliyor`, `bug`. İki haftalık sprint.

## 9. Deney kaydı

Her ölçüm `experiments/reports/` altına `TEMPLATE.md` kopyalanarak yazılır: tarih, kim, config, seed, model/veri sürümü, metrik, yorum. Ölçülmemiş sayı yazılmaz.
