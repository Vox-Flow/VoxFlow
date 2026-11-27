"""Sunum adaptörlerinin paylaştığı etiketler ve TTS yardımcıları."""

from __future__ import annotations

from voice_assistant.domain.schemas import ActionStatus
from voice_assistant.ports.protocols import SpeechSynthesizer

STATUS_LABEL: dict[ActionStatus, str] = {
    ActionStatus.SUCCESS: "✔ başarılı",
    ActionStatus.ERROR: "✖ hata",
    ActionStatus.CANCELLED: "↩ iptal",
    ActionStatus.NEEDS_CLARIFICATION: "? açıklama gerekli",
    ActionStatus.NEEDS_CONFIRMATION: "! onay gerekli",
    ActionStatus.UNSUPPORTED: "– desteklenmiyor",
    ActionStatus.UNKNOWN: "? anlaşılamadı",
}

#: rich stil adları; düz metin adaptörü bunları yok sayar.
STATUS_STYLE: dict[ActionStatus, str] = {
    ActionStatus.SUCCESS: "green",
    ActionStatus.ERROR: "bold red",
    ActionStatus.CANCELLED: "cyan",
    ActionStatus.NEEDS_CLARIFICATION: "yellow",
    ActionStatus.NEEDS_CONFIRMATION: "bold yellow",
    ActionStatus.UNSUPPORTED: "magenta",
    ActionStatus.UNKNOWN: "magenta",
}

TTS_FAILED_NOTE = "[tts: ses üretilemedi, yalnızca metin]"


def label_for(status: ActionStatus) -> str:
    return STATUS_LABEL.get(status, status.value)


def style_for(status: ActionStatus) -> str:
    return STATUS_STYLE.get(status, "white")


def speak_and_needs_note(tts: SpeechSynthesizer | None, message: str) -> bool:
    """Mesajın ilk satırını seslendirmeyi dener.

    Kullanıcıya ``TTS_FAILED_NOTE`` düşülmesi gerekiyorsa True döner: TTS gerçek
    ses üretmeyi vadettiği hâlde üretemediyse. Konsol fallback'i sessizdir, not
    gerektirmez.
    """
    if tts is None or not tts.is_available():
        return False
    spoken = tts.speak(message.splitlines()[0])
    return not spoken and tts.name != "console"
