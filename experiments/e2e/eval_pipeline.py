"""Uçtan uca değerlendirme: metin (referans veya ASR çıktısı) → NLU → diyalog → işlem.

Ölçülen: niyet doğruluğu (NLU katmanı) ve **işlem başarı oranı** (doğru handler, doğru
parametre; mock launcher + bellek içi depo, gerçek uygulama/URL açılmaz).

Kullanım:
  uv run python experiments/e2e/eval_pipeline.py datasets/manifests/nlu_dev_v1.jsonl
  uv run python experiments/e2e/eval_pipeline.py asr_hyp.jsonl --text-field hypothesis
  (ikincisi ASR çıktısıyla koşar)

Manifest satırı: utterance, intent, slots, dialogue_context (docs/dataset_protocol.md).
ASR modu için satırda ek olarak `hypothesis` (Whisper çıktısı) bulunur; gold etiketler aynı kalır.
Bkz. docs/evaluation_protocol.md
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from voice_assistant.adapters.nlu.rule_based import RuleBasedInterpreter  # noqa: E402
from voice_assistant.adapters.platforms.launcher import AllowlistLauncher  # noqa: E402
from voice_assistant.adapters.storage.json_store import InMemoryStore  # noqa: E402
from voice_assistant.config import load_apps, load_sites  # noqa: E402
from voice_assistant.domain.dialogue import DialogueState, PendingAction, PendingConfirmation  # noqa: E402
from voice_assistant.domain.schemas import ActionStatus, Intent  # noqa: E402
from voice_assistant.services.assistant import Assistant  # noqa: E402
from voice_assistant.services.dates import find_date  # noqa: E402
from voice_assistant.services.dialogue_manager import DialogueManager  # noqa: E402
from voice_assistant.services.dispatcher import ActionDispatcher  # noqa: E402
from voice_assistant.services.validator import CommandValidator  # noqa: E402

REFERENCE_TODAY = date(2026, 10, 19)


class SpyLauncher(AllowlistLauncher):
    """Gerçek uygulama/URL açmaz; çağrıları kaydeder."""

    def __init__(self, apps, sites):  # type: ignore[no-untyped-def]
        self.calls: list[tuple[str, str]] = []
        super().__init__(
            apps,
            sites,
            platform_name="linux",
            spawn=lambda argv: None,
            open_url=lambda url: True,
            which=lambda exe: f"/usr/bin/{exe}",
        )

    def open_app(self, key: str) -> str:
        self.calls.append(("open_app", key))
        return super().open_app(key)

    def open_site(self, key: str) -> str:
        self.calls.append(("open_site", key))
        return super().open_site(key)


def build(apps, sites):  # type: ignore[no-untyped-def]
    store = InMemoryStore()
    launcher = SpyLauncher(apps, sites)
    interp = RuleBasedInterpreter(
        {k: v.aliases for k, v in apps.items()},
        {k: v.aliases for k, v in sites.items()},
        today_provider=lambda: REFERENCE_TODAY,
    )
    assistant = Assistant(
        interp,
        DialogueManager(CommandValidator(set(apps), set(sites))),
        ActionDispatcher(store, launcher),
        store,
        record_history=True,
    )
    return assistant, store, launcher


def seed_state(assistant: Assistant, ctx: dict | None) -> None:  # type: ignore[type-arg]
    assistant.state = DialogueState()
    if not ctx:
        return
    if "pending" in ctx:
        intent, param = ctx["pending"].split(".")
        assistant.state.pending_action = PendingAction(
            intent=Intent(intent), missing_parameter=param, question="?"
        )
    if "pending_confirmation" in ctx:
        assistant.state.pending_confirmation = PendingConfirmation(
            intent=Intent(ctx["pending_confirmation"]), question="?"
        )


def expected_action(row: dict) -> tuple[str, dict]:  # type: ignore[type-arg]
    """Gold etiketten beklenen gözlemlenebilir sonuç."""
    intent, slots = row["intent"], dict(row.get("slots", {}))
    if "date_text" in slots:
        dm = find_date(slots.pop("date_text"), REFERENCE_TODAY)
        slots["date"] = dm.value.isoformat() if dm else None
    if intent == "create_task":
        if "title" not in slots:
            return "ask", {"status": ActionStatus.NEEDS_CLARIFICATION}
        return "task", {"title": slots["title"], "date": slots.get("date")}
    if intent == "create_note":
        if "content" not in slots:
            return "ask", {"status": ActionStatus.NEEDS_CLARIFICATION}
        return "note", {"content": slots["content"]}
    if intent == "open_app":
        return (
            ("open_app", {"key": slots["app"]})
            if "app" in slots
            else ("ask", {"status": ActionStatus.NEEDS_CLARIFICATION})
        )
    if intent == "open_website":
        return (
            ("open_site", {"key": slots["site"]})
            if "site" in slots
            else ("ask", {"status": ActionStatus.NEEDS_CLARIFICATION})
        )
    if intent == "list_tasks":
        return "list", {"date": slots.get("date")}
    if intent == "show_history":
        return "history", {}
    if intent == "clear_history":
        return "confirm", {"status": ActionStatus.NEEDS_CONFIRMATION}
    if intent == "affirm":
        return "cleared", {}
    if intent in ("deny", "cancel"):
        return "cancelled", {"status": ActionStatus.CANCELLED}
    if intent == "unsupported":
        return "noop", {"status": ActionStatus.UNSUPPORTED}
    return "noop", {"status": ActionStatus.UNKNOWN}


def observe(kind: str, exp: dict, result, store, launcher) -> bool:  # type: ignore[no-untyped-def]
    """Gerçekten olan şey beklenenle örtüşüyor mu?"""
    if kind == "task":
        t = store.list_tasks()
        return (
            len(t) == 1
            and t[0].title.lower() == exp["title"].lower()
            and ((t[0].date.isoformat() if t[0].date else None) == exp["date"])
        )
    if kind == "note":
        n = store.list_notes()
        return len(n) == 1 and n[0].content.lower() == exp["content"].lower()
    if kind in ("open_app", "open_site"):
        return launcher.calls == [(kind, exp["key"])]
    if kind == "list":
        return result.status == ActionStatus.SUCCESS and result.intent == Intent.LIST_TASKS
    if kind == "history":
        return result.status == ActionStatus.SUCCESS and result.intent == Intent.SHOW_HISTORY
    if kind == "cleared":
        return result.status == ActionStatus.SUCCESS and result.intent == Intent.CLEAR_HISTORY
    if kind in ("ask", "confirm", "cancelled", "noop"):
        side_effects = store.list_tasks() or store.list_notes() or launcher.calls
        return result.status == exp["status"] and not side_effects
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument(
        "--text-field", default="utterance", help="utterance (referans) | hypothesis (ASR çıktısı)"
    )
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    apps, sites = load_apps(), load_sites()
    rows = [
        json.loads(line)
        for line in a.manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    intent_ok = action_ok = 0
    failures: list[dict] = []  # type: ignore[type-arg]
    by_intent: Counter[str] = Counter()
    by_intent_ok: Counter[str] = Counter()
    for r in rows:
        assistant, store, launcher = build(apps, sites)  # her örnek temiz durumla
        seed_state(assistant, r.get("dialogue_context"))
        text = r.get(a.text_field, "")
        result = assistant.handle_text(text)
        kind, exp = expected_action(r)
        pred_intent = result.intent.value if result.intent else "none"
        gold = r["intent"]
        # Diyalog niyetleri sonuçta farklı görünebilir: affirm→clear_history, deny/cancel→cancelled
        intent_hit = (
            pred_intent == gold
            or (gold == "affirm" and pred_intent == "clear_history")
            or (gold in ("deny", "cancel") and result.status == ActionStatus.CANCELLED)
        )
        ok = observe(kind, exp, result, store, launcher)
        intent_ok += intent_hit
        action_ok += ok
        by_intent[gold] += 1
        by_intent_ok[gold] += ok
        if not ok:
            failures.append(
                {
                    "id": r["sample_id"],
                    "text": text,
                    "gold": gold,
                    "expected": kind,
                    "got": f"{result.status.value}/{pred_intent}",
                    "msg": result.message.splitlines()[0][:80],
                }
            )
    n = len(rows)
    report = {
        "manifest": str(a.manifest),
        "text_field": a.text_field,
        "n": n,
        "intent_accuracy": round(intent_ok / n, 4),
        "action_success_rate": round(action_ok / n, 4),
        "per_intent_action_success": {
            k: f"{by_intent_ok[k]}/{by_intent[k]}" for k in sorted(by_intent)
        },
        "failures": failures,
    }
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for k in ("manifest", "text_field", "n", "intent_accuracy", "action_success_rate"):
            print(f"{k:22}: {report[k]}")
        for k, v in report["per_intent_action_success"].items():
            print(f"   {k:16} {v}")
        for f in failures:
            print("  HATA:", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
