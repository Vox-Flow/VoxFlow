"""NLU baseline değerlendirme: manifest -> intent accuracy, macro-F1, slot exact match.

Kullanım:
  .venv/bin/python experiments/nlu/eval_rule_based.py datasets/manifests/nlu_synthetic_dev.jsonl

Not: Sentetik dev kümesi üzerindeki sonuç bir "başarı oranı" iddiası değildir;
betiğin ve şemanın çalıştığını gösterir. Gerçek ölçüm için bağımsız test kümesi gerekir.
Aynı betik ileride Qwen (Ollama) ve fine-tuned adaptörlerle --provider ile çalıştırılacaktır.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from voice_assistant.adapters.nlu.rule_based import RuleBasedInterpreter  # noqa: E402
from voice_assistant.config import load_apps, load_sites  # noqa: E402
from voice_assistant.domain.dialogue import DialogueState, PendingAction, PendingConfirmation  # noqa: E402
from voice_assistant.domain.schemas import Intent  # noqa: E402
from voice_assistant.services.dates import find_date  # noqa: E402

REFERENCE_TODAY = date(2026, 10, 19)  # göreli tarihler bu güne göre çözülür (tekrarlanabilirlik)


def build_state(ctx: dict | None) -> DialogueState:  # type: ignore[type-arg]
    st = DialogueState()
    if not ctx:
        return st
    if "pending" in ctx:
        intent, param = ctx["pending"].split(".")
        st.pending_action = PendingAction(
            intent=Intent(intent), missing_parameter=param, question="?"
        )
    if "pending_confirmation" in ctx:
        st.pending_confirmation = PendingConfirmation(
            intent=Intent(ctx["pending_confirmation"]), question="?"
        )
    return st


def expected_slots(slots: dict) -> dict:  # type: ignore[type-arg]
    out = dict(slots)
    if "date_text" in out:
        dm = find_date(out.pop("date_text"), REFERENCE_TODAY)
        if dm:
            out["date"] = dm.value.isoformat()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--provider", default="rule_based", choices=["rule_based"])
    ap.add_argument("--json", action="store_true", help="sonucu JSON olarak yaz")
    args = ap.parse_args()

    apps, sites = load_apps(), load_sites()
    interp = RuleBasedInterpreter(
        {k: v.aliases for k, v in apps.items()},
        {k: v.aliases for k, v in sites.items()},
        today_provider=lambda: REFERENCE_TODAY,
    )

    rows = [
        json.loads(line)
        for line in args.manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    tp: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    fn: Counter[str] = Counter()
    correct = slot_ok = 0
    latencies: list[float] = []
    errors: list[dict] = []  # type: ignore[type-arg]
    for r in rows:
        st = build_state(r.get("dialogue_context"))
        t0 = time.perf_counter()
        res = interp.interpret(r["utterance"], st)
        latencies.append(time.perf_counter() - t0)
        gold, pred = r["intent"], res.intent.value
        if gold == pred:
            correct += 1
            tp[gold] += 1
        else:
            fp[pred] += 1
            fn[gold] += 1
            errors.append(
                {"id": r["sample_id"], "utterance": r["utterance"], "gold": gold, "pred": pred}
            )
        exp = expected_slots(r.get("slots", {}))
        got = {
            k: v
            for k, v in res.parameters.items()
            if k in exp or k in ("title", "content", "app", "site", "date")
        }
        if gold == pred and got == exp:
            slot_ok += 1
        elif gold == pred:
            errors.append(
                {
                    "id": r["sample_id"],
                    "utterance": r["utterance"],
                    "slots_gold": exp,
                    "slots_pred": got,
                }
            )

    labels = sorted(set(r["intent"] for r in rows) | set(fp))
    f1s = []
    for lab in labels:
        p = tp[lab] / (tp[lab] + fp[lab]) if tp[lab] + fp[lab] else 0.0
        rc = tp[lab] / (tp[lab] + fn[lab]) if tp[lab] + fn[lab] else 0.0
        f1s.append(2 * p * rc / (p + rc) if p + rc else 0.0)
    n = len(rows)
    report = {
        "manifest": str(args.manifest),
        "provider": args.provider,
        "n": n,
        "intent_accuracy": round(correct / n, 4) if n else None,
        "macro_f1": round(sum(f1s) / len(f1s), 4) if f1s else None,
        "slot_exact_match": round(slot_ok / n, 4) if n else None,
        "mean_latency_ms": round(1000 * sum(latencies) / n, 3) if n else None,
        "errors": errors,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for k, v in report.items():
            if k != "errors":
                print(f"{k:18}: {v}")
        for e in errors:
            print("  HATA:", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
