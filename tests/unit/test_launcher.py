import pytest
from tests.conftest import SpyLauncher

from voice_assistant.adapters.platforms.launcher import AllowlistLauncher, AppSpec, SiteSpec
from voice_assistant.domain.errors import AppNotFoundError, NotAllowedError


def test_open_app_uses_fixed_argv(launcher: SpyLauncher) -> None:
    assert launcher.open_app("firefox") == "firefox"
    assert launcher.spawned == [("firefox",)]


def test_open_app_not_allowed(launcher: SpyLauncher) -> None:
    with pytest.raises(NotAllowedError):
        launcher.open_app("photoshop")


def test_open_app_missing_binary() -> None:
    launcher = SpyLauncher(which_ok=False)
    with pytest.raises(AppNotFoundError):
        launcher.open_app("firefox")
    assert launcher.spawned == []


def test_open_app_no_command_for_platform() -> None:
    launcher = AllowlistLauncher(
        {"x": AppSpec("x", ("x",), {"windows": ("x.exe",)})},
        {},
        platform_name="linux",
        spawn=lambda a: None,
        open_url=lambda u: True,
    )
    with pytest.raises(AppNotFoundError):
        launcher.open_app("x")


def test_open_site(launcher: SpyLauncher) -> None:
    assert launcher.open_site("youtube") == "https://www.youtube.com"
    assert launcher.opened == ["https://www.youtube.com"]


def test_open_site_not_allowed(launcher: SpyLauncher) -> None:
    with pytest.raises(NotAllowedError):
        launcher.open_site("evil")


def test_invalid_scheme_in_config_rejected() -> None:
    with pytest.raises(NotAllowedError):
        AllowlistLauncher(
            {}, {"f": SiteSpec("f", "file:///etc/passwd", ("f",))}, platform_name="linux"
        )
