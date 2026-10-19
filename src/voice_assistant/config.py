"""Uygulama yapılandırması (Pydantic). Örnek dosyalar config/*.example.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from voice_assistant.adapters.platforms.launcher import AppSpec, SiteSpec
from voice_assistant.domain.errors import ConfigError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


class AsrConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["mock", "faster_whisper"] = "mock"
    model_size: str = "base"
    device: str = "auto"
    compute_type: str = "int8"


class NluConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["rule_based", "ollama"] = "rule_based"
    ollama_model: str = "qwen2.5:latest"
    ollama_url: str = "http://127.0.0.1:11434"
    timeout_s: float = 30


class TtsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["console", "pyttsx3"] = "console"


class AudioConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_rate: int = 16000
    channels: int = 1
    max_seconds: int = Field(default=60, ge=1, le=600)


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: str = "tr"
    data_dir: str | None = None
    asr: AsrConfig = Field(default_factory=AsrConfig)
    nlu: NluConfig = Field(default_factory=NluConfig)
    tts: TtsConfig = Field(default_factory=TtsConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)


def _load_json(path: Path) -> dict:  # type: ignore[type-arg]
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"Yapılandırma dosyası yok: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Yapılandırma dosyası geçersiz JSON: {path} ({exc})") from exc


def _resolve(name: str, config_dir: Path) -> Path:
    """config/<name>.json varsa onu, yoksa <name>.example.json'ı kullan."""
    real = config_dir / f"{name}.json"
    return real if real.exists() else config_dir / f"{name}.example.json"


def load_app_config(path: Path | None = None, config_dir: Path = CONFIG_DIR) -> AppConfig:
    p = path or _resolve("app", config_dir)
    try:
        return AppConfig.model_validate(_load_json(p))
    except PydanticValidationError as exc:
        raise ConfigError(f"app config hatalı ({p}): {exc.errors()[0]['msg']}") from exc


def load_apps(path: Path | None = None, config_dir: Path = CONFIG_DIR) -> dict[str, AppSpec]:
    p = path or _resolve("apps", config_dir)
    doc = _load_json(p)
    apps = doc.get("apps")
    if not isinstance(apps, dict):
        raise ConfigError(f"{p}: 'apps' sözlüğü bekleniyor.")
    out: dict[str, AppSpec] = {}
    for key, spec in apps.items():
        if not isinstance(spec, dict):
            raise ConfigError(f"{p}: '{key}' tanımı sözlük olmalı.")
        aliases = spec.get("aliases", [key])
        commands: dict[str, tuple[str, ...]] = {}
        for plat in ("linux", "windows", "macos"):
            argv = spec.get(plat)
            if argv is None:
                continue
            if not isinstance(argv, list) or not all(isinstance(a, str) and a for a in argv):
                raise ConfigError(f"{p}: '{key}.{plat}' boş olmayan metin listesi olmalı.")
            commands[plat] = tuple(argv)
        out[key] = AppSpec(key=key, aliases=tuple(aliases), commands=commands)
    return out


def load_sites(path: Path | None = None, config_dir: Path = CONFIG_DIR) -> dict[str, SiteSpec]:
    p = path or _resolve("sites", config_dir)
    doc = _load_json(p)
    sites = doc.get("sites")
    if not isinstance(sites, dict):
        raise ConfigError(f"{p}: 'sites' sözlüğü bekleniyor.")
    out: dict[str, SiteSpec] = {}
    for key, spec in sites.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("url"), str):
            raise ConfigError(f"{p}: '{key}' için 'url' zorunlu.")
        out[key] = SiteSpec(key=key, url=spec["url"], aliases=tuple(spec.get("aliases", [key])))
    return out
