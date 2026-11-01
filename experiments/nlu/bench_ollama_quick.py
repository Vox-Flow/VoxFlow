"""Hızlı NLU model kıyası (Ollama, JSON modu). Helin'in OllamaInterpreter adaptörü (#5) bu prompt'u temel alabilir.

Kullanım: uv run python experiments/nlu/bench_ollama_quick.py qwen2.5:3b gemma3:4b
Ollama sunucusu açık olmalı; model yoksa indirmez, hata verir.
import json, sys, time, urllib.request
from collections import Counter
sys.path.insert(0, "src")
from voice_assistant.domain.schemas import Intent, IntentResult

MODELS = sys.argv[1:]
rows = [json.loads(l) for l in open("datasets/manifests/nlu_dev_v1.jsonl", encoding="utf-8") if l.strip()]
APPS = ["firefox", "hesap_makinesi", "metin_editoru", "terminal", "dosya_yoneticisi"]
SITES = ["youtube", "google", "github", "wikipedia", "ekampus"]
SYSTEM = f"""Sen Türkçe bir sesli asistanın niyet sınıflandırıcısısın. Kullanıcı cümlesini SADECE şu JSON şemasıyla yanıtla:
{{"intent": <niyet>, "parameters": {{...}}}}
Niyetler: open_app (parameters.app ∈ {APPS}), open_website (parameters.site ∈ {SITES}), create_note (parameters.content: not metni),
create_task (parameters.title: görev adı, parameters.date_text: varsa tarih ifadesi ham hâliyle), list_tasks (parameters.date_text isteğe bağlı),
show_history, clear_history, cancel (iptal/vazgeçtim), affirm (evet/onay; yalnızca onay bekleniyorsa), deny (hayır; yalnızca onay bekleniyorsa),
unsupported (anlaşıldı ama desteklenmiyor: silme, düzenleme, tamamlama, müzik, mesaj, hava, saat, kapatma, dosya, serbest komut),
unknown (anlaşılamadı veya boş). Uygulama/site izin listesinde yoksa intent'i yine open_app/open_website yap ama app/site verme.
Yalnızca JSON döndür, açıklama yazma.
Örnekler:
"not al" → {{"intent":"create_note","parameters":{{}}}}
"not al ekmek al" → {{"intent":"create_note","parameters":{{"content":"ekmek al"}}}}
"görevlerimi göster" → {{"intent":"list_tasks","parameters":{{}}}}
"geçmişi göster" → {{"intent":"show_history","parameters":{{}}}}
"youtube'u aç" → {{"intent":"open_website","parameters":{{"site":"youtube"}}}}
"notu sil" → {{"intent":"unsupported","parameters":{{}}}}
"hayır" (onay bekleniyor) → {{"intent":"deny","parameters":{{}}}}
"merhaba nasılsın" → {{"intent":"unknown","parameters":{{}}}}"""

def ctx(c):
    if not c: return "Bağlam: bekleyen işlem yok."
    if "pending" in c: return f"Bağlam: '{c['pending'].split('.')[0]}' için eksik bilgi bekleniyor; kullanıcı doğrudan o bilgiyi söyleyebilir."
    return "Bağlam: geçmiş silme için evet/hayır onayı bekleniyor."

def ask(model, r):
    body = {"model": model, "format": "json", "stream": False, "options": {"temperature": 0, "num_predict": 120},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": ctx(r["dialogue_context"]) + "\nCümle: " + json.dumps(r["utterance"], ensure_ascii=False)}]}
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    out = json.loads(urllib.request.urlopen(req, timeout=120).read())["message"]["content"]
    return out, time.perf_counter() - t0

for model in MODELS:
    # ısınma
    try: ask(model, rows[0])
    except Exception as e: print(model, "HATA", e); continue
    ok = valid = slot_ok = 0; lat = []; conf = Counter(); errs = []
    for r in rows:
        try: out, dt = ask(model, r)
        except Exception as e: out, dt = "", 0
        lat.append(dt)
        try:
            d = json.loads(out); ir = IntentResult.model_validate({"intent": d.get("intent"), "parameters": d.get("parameters") or {}}); valid += 1
            pred = ir.intent.value; params = ir.parameters
        except Exception:
            pred, params = "invalid", {}
        gold = r["intent"]
        if pred == gold: ok += 1
        else: conf[(gold, pred)] += 1; errs.append((r["utterance"], gold, pred))
        exp = r["slots"]; got = {k: params.get(k) for k in exp}
        if pred == gold and all(str(got.get(k, "")).strip().lower() == str(v).lower() for k, v in exp.items()) and not (set(params) & {"app", "site"} - set(exp)): slot_ok += 1
    n = len(rows); lat.sort()
    print(f"\n=== {model} ===")
    print(f"intent_acc={ok/n:.3f}  slot_em={slot_ok/n:.3f}  valid_json={valid/n:.3f}  lat_mean={sum(lat)/n:.2f}s  lat_p50={lat[n//2]:.2f}s  lat_max={lat[-1]:.2f}s")
    print("hatalar (gold→pred):", conf.most_common(8))
    for u, g, p in errs[:6]: print("   ", repr(u), g, "→", p)
