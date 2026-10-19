"""Uygulama genelinde kullanılan hata sınıfları ve hata kodları."""

from __future__ import annotations


class VoxFlowError(Exception):
    """Tüm uygulama hatalarının temel sınıfı. `code` makine tarafından okunur."""

    code: str = "E_GENERIC"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code
        self.message = message


class ConfigError(VoxFlowError):
    code = "E_CONFIG"


class ValidationError(VoxFlowError):
    code = "E_VALIDATION"


class StoreError(VoxFlowError):
    code = "E_STORE"


class StoreCorruptedError(StoreError):
    code = "E_STORE_CORRUPTED"


class ActionError(VoxFlowError):
    code = "E_ACTION"


class AppNotFoundError(ActionError):
    code = "E_APP_NOT_FOUND"


class NotAllowedError(ActionError):
    code = "E_NOT_ALLOWED"


class AudioError(VoxFlowError):
    code = "E_AUDIO"


class AsrUnavailableError(VoxFlowError):
    code = "E_ASR_UNAVAILABLE"


class NluUnavailableError(VoxFlowError):
    code = "E_NLU_UNAVAILABLE"
