"""Bağımlılık bağlama: config'e göre adaptörleri seçer ve Assistant'ı kurar."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from voice_assistant.adapters.asr.mock import MockRecognizer
from voice_assistant.adapters.nlu.rule_based import RuleBasedInterpreter
from voice_assistant.adapters.platforms.launcher import AllowlistLauncher
from voice_assistant.adapters.storage.json_store import JsonStore, default_data_dir
from voice_assistant.adapters.tts.console import ConsoleSynthesizer
from voice_assistant.config import AppConfig, load_app_config, load_apps, load_sites
from voice_assistant.ports.protocols import IntentInterpreter, SpeechRecognizer, SpeechSynthesizer
from voice_assistant.services.assistant import Assistant
from voice_assistant.services.dialogue_manager import DialogueManager
from voice_assistant.services.dispatcher import ActionDispatcher
from voice_assistant.services.validator import CommandValidator

log = logging.getLogger("voxflow.wiring")


@dataclass
class Container:
    config: AppConfig
    assistant: Assistant
    recognizer: SpeechRecognizer
    tts: SpeechSynthesizer
    launcher: AllowlistLauncher
    store: JsonStore
    warnings: list[str]


def build_interpreter(
    cfg: AppConfig, launcher: AllowlistLauncher, warnings: list[str]
) -> IntentInterpreter:
    rule = RuleBasedInterpreter(launcher.app_aliases(), launcher.site_aliases())
    if cfg.nlu.provider in ("ollama", "hybrid"):
        try:
            from voice_assistant.adapters.nlu.ollama_qwen import HybridInterpreter, OllamaInterpreter

            llm = OllamaInterpreter(
                model=cfg.nlu.ollama_model,
                base_url=cfg.nlu.ollama_url,
                timeout_s=cfg.nlu.timeout_s,
                allowed_apps=sorted(launcher.apps),
                allowed_sites=sorted(launcher.sites),
                fallback=rule,
            )
            if not llm.is_available():
                warnings.append("Ollama sunucusuna ulaşılamadı; kurallı yorumlayıcı kullanılıyor.")
                return rule
            if cfg.nlu.provider == "hybrid":
                return HybridInterpreter(rule_based=rule, ollama=llm)
            return llm
        except Exception as exc:  # noqa: BLE001
            warnings.append(
                f"Ollama adaptörü yüklenemedi ({exc}); kurallı yorumlayıcı kullanılıyor."
            )
    return rule


def build_recognizer(cfg: AppConfig, warnings: list[str]) -> SpeechRecognizer:
    if cfg.asr.provider == "faster_whisper":
        from voice_assistant.adapters.asr.faster_whisper_adapter import FasterWhisperRecognizer

        rec = FasterWhisperRecognizer(cfg.asr.model_size, cfg.asr.device, cfg.asr.compute_type)
        return rec
    warnings.append("ASR sağlayıcı 'mock': sesli mod gerçek transkripsiyon yapmaz.")
    return MockRecognizer()


def build_tts(cfg: AppConfig, warnings: list[str]) -> SpeechSynthesizer:
    if cfg.tts.provider == "pyttsx3":
        from voice_assistant.adapters.tts.pyttsx3_tts import Pyttsx3Synthesizer

        tts = Pyttsx3Synthesizer()
        if not tts.is_available():
            warnings.append("pyttsx3 kullanılamıyor; sessiz fallback.")
            return ConsoleSynthesizer()
        return tts
    return ConsoleSynthesizer()


def build_container(
    config_path: Path | None = None,
    data_dir: Path | None = None,
    *,
    record_history: bool = True,
) -> Container:
    warnings: list[str] = []
    cfg = load_app_config(config_path)
    apps = load_apps()
    sites = load_sites()
    launcher = AllowlistLauncher(apps, sites)
    store = JsonStore(
        data_dir or (Path(cfg.data_dir).expanduser() if cfg.data_dir else default_data_dir())
    )
    validator = CommandValidator(set(apps), set(sites))
    interpreter = build_interpreter(cfg, launcher, warnings)
    assistant = Assistant(
        interpreter,
        DialogueManager(validator),
        ActionDispatcher(store, launcher),
        store,
        record_history=record_history,
    )
    return Container(
        config=cfg,
        assistant=assistant,
        recognizer=build_recognizer(cfg, warnings),
        tts=build_tts(cfg, warnings),
        launcher=launcher,
        store=store,
        warnings=warnings,
    )
