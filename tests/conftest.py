from __future__ import annotations

from datetime import date

import pytest

from voice_assistant.adapters.nlu.rule_based import RuleBasedInterpreter
from voice_assistant.adapters.platforms.launcher import AllowlistLauncher, AppSpec, SiteSpec
from voice_assistant.adapters.storage.json_store import InMemoryStore, JsonStore
from voice_assistant.services.assistant import Assistant
from voice_assistant.services.dialogue_manager import DialogueManager
from voice_assistant.services.dispatcher import ActionDispatcher
from voice_assistant.services.validator import CommandValidator

TODAY = date(2026, 10, 19)  # Pazartesi — testlerde sabit "bugün"

APPS = {
    "firefox": AppSpec(
        "firefox", ("firefox", "tarayıcı"), {"linux": ("firefox",), "windows": ("firefox.exe",)}
    ),
    "hesap_makinesi": AppSpec(
        "hesap_makinesi", ("hesap makinesi", "hesap makinesini"), {"linux": ("gnome-calculator",)}
    ),
}
SITES = {
    "youtube": SiteSpec("youtube", "https://www.youtube.com", ("youtube", "yutup")),
    "github": SiteSpec("github", "https://github.com", ("github",)),
    "wikipedia": SiteSpec("wikipedia", "https://tr.wikipedia.org", ("wikipedia", "vikipedi")),
    "ekampus": SiteSpec("ekampus", "https://example.edu", ("e kampüs", "ekampüs", "okul sitesi")),
}


class SpyLauncher(AllowlistLauncher):
    def __init__(self, which_ok: bool = True) -> None:
        self.spawned: list[tuple[str, ...]] = []
        self.opened: list[str] = []
        super().__init__(
            APPS,
            SITES,
            platform_name="linux",
            spawn=lambda argv: self.spawned.append(tuple(argv)),
            open_url=lambda url: self.opened.append(url) or True,
            which=(lambda exe: f"/usr/bin/{exe}") if which_ok else (lambda exe: None),
        )


@pytest.fixture
def launcher() -> SpyLauncher:
    return SpyLauncher()


@pytest.fixture
def interpreter(launcher: SpyLauncher) -> RuleBasedInterpreter:
    return RuleBasedInterpreter(
        launcher.app_aliases(), launcher.site_aliases(), today_provider=lambda: TODAY
    )


@pytest.fixture
def store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def json_store(tmp_path) -> JsonStore:  # type: ignore[no-untyped-def]
    return JsonStore(tmp_path / "data")


def make_assistant(interpreter, store, launcher) -> Assistant:  # type: ignore[no-untyped-def]
    validator = CommandValidator(set(APPS), set(SITES))
    return Assistant(
        interpreter, DialogueManager(validator), ActionDispatcher(store, launcher), store
    )


@pytest.fixture
def assistant(interpreter, store, launcher) -> Assistant:  # type: ignore[no-untyped-def]
    return make_assistant(interpreter, store, launcher)
