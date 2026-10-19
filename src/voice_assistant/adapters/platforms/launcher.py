"""Allowlist tabanlı uygulama ve web sitesi başlatıcı.

Güvenlik ilkeleri:
- Komut satırı yalnızca konfigürasyondan gelen sabit argüman listesidir (shell=False).
- Kullanıcı metni asla komuta veya URL'ye eklenmez; yalnızca allowlist anahtarı seçilir.
- Uygulama PATH'te yoksa anlaşılır hata (E_APP_NOT_FOUND).
- webbrowser.open yalnızca "açma isteği gönderildi" anlamına gelir; yüklendi denmez.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import webbrowser
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from urllib.parse import urlparse

from voice_assistant.domain.errors import AppNotFoundError, NotAllowedError

Platform = str  # "linux" | "windows" | "macos"


def current_platform() -> Platform:
    s = platform.system().lower()
    if s.startswith("win"):
        return "windows"
    if s == "darwin":
        return "macos"
    return "linux"


@dataclass(frozen=True)
class AppSpec:
    key: str
    aliases: tuple[str, ...]
    commands: dict[Platform, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class SiteSpec:
    key: str
    url: str
    aliases: tuple[str, ...]


def _validate_url(url: str) -> str:
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise NotAllowedError(f"Allowlist'teki URL geçersiz: {url!r} (yalnızca http/https).")
    return url


class AllowlistLauncher:
    def __init__(
        self,
        apps: dict[str, AppSpec],
        sites: dict[str, SiteSpec],
        *,
        platform_name: Platform | None = None,
        spawn: Callable[[Sequence[str]], None] | None = None,
        open_url: Callable[[str], bool] | None = None,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.apps = apps
        self.sites = sites
        self.platform = platform_name or current_platform()
        self._spawn = spawn or self._default_spawn
        self._open_url = open_url or (lambda u: webbrowser.open(u, new=2))
        self._which = which
        for s in sites.values():
            _validate_url(s.url)

    @staticmethod
    def _default_spawn(argv: Sequence[str]) -> None:
        # shell=False; argv sabit; çıktıyı terminale bulaştırma; oturumdan ayır.
        subprocess.Popen(  # noqa: S603 - argv allowlist'ten gelir, kullanıcı girdisi içermez
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def app_aliases(self) -> dict[str, tuple[str, ...]]:
        return {k: v.aliases for k, v in self.apps.items()}

    def site_aliases(self) -> dict[str, tuple[str, ...]]:
        return {k: v.aliases for k, v in self.sites.items()}

    def open_app(self, key: str) -> str:
        """Uygulamayı başlatır; başlatılan komutun adını döndürür."""
        spec = self.apps.get(key)
        if spec is None:
            raise NotAllowedError(f"'{key}' izin verilen uygulamalar arasında değil.")
        argv = spec.commands.get(self.platform)
        if not argv:
            raise AppNotFoundError(
                f"'{key}' için {self.platform} platformunda komut tanımlı değil."
            )
        exe = argv[0]
        if self._which(exe) is None:
            raise AppNotFoundError(
                f"'{exe}' bu bilgisayarda bulunamadı. Kurulu değilse kurun ya da "
                "config/apps.json'da yolu düzeltin."
            )
        self._spawn(argv)
        return exe

    def open_site(self, key: str) -> str:
        """Tarayıcıya açma isteği gönderir; URL'yi döndürür. Yüklendiğini garanti etmez."""
        spec = self.sites.get(key)
        if spec is None:
            raise NotAllowedError(f"'{key}' izin verilen siteler arasında değil.")
        url = _validate_url(spec.url)
        ok = self._open_url(url)
        if not ok:
            raise AppNotFoundError("Tarayıcıya açma isteği iletilemedi (webbrowser False döndü).")
        return url
