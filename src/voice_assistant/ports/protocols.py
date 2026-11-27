"""Port (arayüz) sözleşmeleri. Gerçek, kurallı ve mock adaptörler bunları uygular.

Protocol kullanıldığı için adaptörlerin bu sınıflardan miras alması gerekmez;
yapısal uyum (duck typing) yeterlidir ve mypy ile denetlenir.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from voice_assistant.domain.dialogue import DialogueState
from voice_assistant.domain.schemas import (
    ActionResult,
    HistoryEntry,
    IntentResult,
    Note,
    Task,
    Transcript,
    ValidatedCommand,
)


class AudioClip(Protocol):
    """Bellekte tutulan tek kanallı PCM ses. Kalıcı dosyaya yazılmaz."""

    @property
    def sample_rate(self) -> int: ...

    @property
    def duration_s(self) -> float: ...

    def to_float32(self) -> object:
        """numpy float32 dizisi (-1..1) döndürür; numpy isteğe bağlı olduğu için object."""
        ...


@runtime_checkable
class AudioCapture(Protocol):
    """Mikrofon kaydını başlatır/durdurur. Kayıt sırasında ham ses yalnızca bellekte."""

    def start(self) -> None: ...

    def stop(self) -> AudioClip: ...

    def close(self) -> None: ...


@runtime_checkable
class SpeechRecognizer(Protocol):
    """Ses -> Türkçe metin. task=transcribe; çeviri yapılmaz."""

    @property
    def name(self) -> str: ...

    def is_available(self) -> bool: ...

    def transcribe(self, clip: AudioClip) -> Transcript: ...


@runtime_checkable
class IntentInterpreter(Protocol):
    """Metin + kısa diyalog durumu -> yapılandırılmış niyet. Çıktı güvenilmez sayılır."""

    @property
    def name(self) -> str: ...

    def interpret(self, text: str, state: DialogueState) -> IntentResult: ...


@runtime_checkable
class ActionExecutor(Protocol):
    """Doğrulanmış komut -> gerçek sonuç. Yalnızca kayıtlı Python fonksiyonları çalışır."""

    def execute(self, command: ValidatedCommand) -> ActionResult: ...


@runtime_checkable
class SpeechSynthesizer(Protocol):
    """Metin -> yerel ses. Yoksa açıkça sessiz fallback."""

    @property
    def name(self) -> str: ...

    def is_available(self) -> bool: ...

    def speak(self, text: str) -> bool:
        """Konuşma gerçekten üretildiyse True, sessiz fallback'e düşüldüyse False."""
        ...


@runtime_checkable
class Store(Protocol):
    """Kalıcı depo. Kapsam bilerek dar: ekle/listele; düzenleme/silme yok (geçmiş hariç)."""

    def add_note(self, content: str) -> Note: ...

    def add_task(self, title: str, due: date | None) -> Task: ...

    def list_tasks(self, due: date | None = None) -> list[Task]: ...

    def append_history(self, entry: HistoryEntry) -> None: ...

    def list_history(self, limit: int | None = None) -> list[HistoryEntry]: ...

    def clear_history(self) -> int:
        """Silinen kayıt sayısını döndürür."""
        ...
