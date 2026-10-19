"""CommandValidator: IntentResult -> ValidatedCommand.

Şema + allowlist + tarih + zorunlu alan doğrulaması. Bilinmeyen parametreler
atılır; zorunlu alan eksikse hangi alanın eksik olduğunu bildirir. Bu katman
LLM veya kural çıktısına güvenmez.
"""

from __future__ import annotations

from dataclasses import dataclass

from voice_assistant.domain.schemas import (
    ACTION_INTENTS,
    ALLOWED_PARAMETERS,
    CONFIRMATION_REQUIRED,
    REQUIRED_PARAMETERS,
    Intent,
    IntentResult,
    ValidatedCommand,
)
from voice_assistant.services.dates import parse_iso_date

MAX_TITLE = 300
MAX_NOTE = 2000

CLARIFICATION_QUESTIONS: dict[tuple[Intent, str], str] = {
    (Intent.CREATE_TASK, "title"): "Görevin adı ne olsun?",
    (Intent.CREATE_NOTE, "content"): "Not içeriği ne olsun?",
    (Intent.OPEN_APP, "app"): "Hangi uygulamayı açayım?",
    (Intent.OPEN_WEBSITE, "site"): "Hangi siteyi açayım?",
}


@dataclass(frozen=True)
class ValidationOutcome:
    command: ValidatedCommand | None = None
    missing_parameter: str | None = None
    question: str | None = None
    error: str | None = None
    needs_confirmation: bool = False

    @property
    def ok(self) -> bool:
        return self.command is not None and self.error is None


class CommandValidator:
    def __init__(self, allowed_apps: set[str], allowed_sites: set[str]) -> None:
        self.allowed_apps = set(allowed_apps)
        self.allowed_sites = set(allowed_sites)

    def validate(self, result: IntentResult, *, confirmed: bool = False) -> ValidationOutcome:
        intent = result.intent
        if intent not in ACTION_INTENTS:
            return ValidationOutcome(error=f"'{intent}' bir eylem niyeti değil.")

        allowed = ALLOWED_PARAMETERS[intent]
        params: dict[str, str | int | None] = {}
        for k, v in result.parameters.items():
            if k not in allowed:
                continue  # bilinmeyen anahtar: sessizce at, asla işlem başlatma
            if isinstance(v, bool):
                continue
            if isinstance(v, str):
                v = v.strip()
                if not v:
                    continue
            params[k] = v  # type: ignore[assignment]

        # Alan bazlı doğrulama
        if "title" in params:
            if not isinstance(params["title"], str) or len(params["title"]) > MAX_TITLE:
                return ValidationOutcome(error=f"Görev adı en fazla {MAX_TITLE} karakter olmalı.")
        if "content" in params:
            if not isinstance(params["content"], str) or len(params["content"]) > MAX_NOTE:
                return ValidationOutcome(error=f"Not en fazla {MAX_NOTE} karakter olmalı.")
        if "date" in params:
            d = parse_iso_date(str(params["date"]))
            if d is None:
                return ValidationOutcome(
                    error="Tarih anlaşılamadı. 'yarın', 'pazartesi' ya da '20 ekim' gibi söyleyin."
                )
            params["date"] = d.isoformat()
        if "limit" in params:
            try:
                lim = int(params["limit"])  # type: ignore[arg-type]
            except (TypeError, ValueError):
                lim = 10
            params["limit"] = max(1, min(lim, 100))
        if "app" in params and params["app"] not in self.allowed_apps:
            return ValidationOutcome(
                error=f"'{params['app']}' izin verilen uygulamalar arasında değil. "
                f"İzinli: {', '.join(sorted(self.allowed_apps)) or '(boş)'}"
            )
        if "site" in params and params["site"] not in self.allowed_sites:
            return ValidationOutcome(
                error=f"'{params['site']}' izin verilen siteler arasında değil. "
                f"İzinli: {', '.join(sorted(self.allowed_sites)) or '(boş)'}"
            )

        for req in sorted(REQUIRED_PARAMETERS[intent]):
            if req not in params:
                q = result.clarification_question or CLARIFICATION_QUESTIONS.get(
                    (intent, req), f"'{req}' bilgisi eksik, belirtir misiniz?"
                )
                return ValidationOutcome(missing_parameter=req, question=q)

        cmd = ValidatedCommand(intent=intent, parameters=params, confirmed=confirmed)
        if intent in CONFIRMATION_REQUIRED and not confirmed:
            return ValidationOutcome(command=cmd, needs_confirmation=True)
        return ValidationOutcome(command=cmd)
