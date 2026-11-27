"""`eval_pipeline.py --provider`: yorumlayıcı seçimi.

Uçtan uca ölçüm şimdiye dek yalnızca kurallı çözümleyiciyi destekliyordu, bu
yüzden hibritin işlem başarısı hiç ölçülemedi. Bu testler seçimin doğru tipi
kurduğunu ve varsayılanın değişmediğini korur (Ollama'ya ağ çağrısı yapılmaz).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "e2e"))

from eval_pipeline import build_interpreter  # noqa: E402

from voice_assistant.adapters.nlu.rule_based import RuleBasedInterpreter  # noqa: E402
from voice_assistant.config import load_apps, load_sites  # noqa: E402

APPS, SITES = load_apps(), load_sites()


def _build(provider: str):  # type: ignore[no-untyped-def]
    return build_interpreter(provider, APPS, SITES, "qwen2.5:3b", "http://127.0.0.1:11434")


def test_default_provider_is_rule_based() -> None:
    assert isinstance(_build("rule_based"), RuleBasedInterpreter)


def test_hybrid_wraps_rule_based_as_first_step() -> None:
    from voice_assistant.adapters.nlu.ollama_qwen import HybridInterpreter

    interp = _build("hybrid")
    assert isinstance(interp, HybridInterpreter)
    assert isinstance(interp._rule_based, RuleBasedInterpreter)


def test_ollama_falls_back_to_rule_based() -> None:
    """Ollama kapalıyken bile sistem çalışmaya devam etmeli (ADR-009)."""
    from voice_assistant.adapters.nlu.ollama_qwen import OllamaInterpreter

    interp = _build("ollama")
    assert isinstance(interp, OllamaInterpreter)
    assert isinstance(interp._fallback, RuleBasedInterpreter)
