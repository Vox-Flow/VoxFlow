"""Giriş aygıtlarını listeleme ve seçme.

Windows doğrulamasında (#12) varsayılan giriş aygıtı sanal bir ses kablosuydu;
kayıt sessiz çıkıyordu ve kullanıcının başka bir mikrofon seçmesinin yolu yoktu.
Bu modül aygıtları listeler ve ad/indeksle seçmeyi sağlar.
"""

from __future__ import annotations

from dataclasses import dataclass

from voice_assistant.domain.errors import AudioError


@dataclass(frozen=True)
class InputDevice:
    index: int
    name: str
    channels: int
    default_sample_rate: float
    is_default: bool
    host_api: str = ""

    def describe(self) -> str:
        isaret = "*" if self.is_default else " "
        api = f" [{self.host_api}]" if self.host_api else ""
        return (
            f"{isaret} {self.index:>3}  {self.name}{api} "
            f"({self.channels} kanal, {self.default_sample_rate:.0f} Hz)"
        )


def list_input_devices() -> list[InputDevice]:
    """Giriş kanalı olan aygıtları döndürür. Varsayılan olan işaretlenir."""
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise AudioError("Aygıt listesi için 'sounddevice' gerekli: uv sync --extra audio") from exc

    try:
        default_index = sd.default.device[0]
    except (TypeError, IndexError):  # pragma: no cover - sounddevice sürümüne bağlı
        default_index = None

    try:
        host_apis = list(sd.query_hostapis())
    except Exception:  # noqa: BLE001 - PortAudio hataları çeşitli tiplerde gelir
        host_apis = []

    devices: list[InputDevice] = []
    for index, info in enumerate(sd.query_devices()):
        channels = int(info.get("max_input_channels", 0))
        if channels <= 0:
            continue
        api_index = info.get("hostapi")
        api_name = ""
        if isinstance(api_index, int) and 0 <= api_index < len(host_apis):
            api_name = str(host_apis[api_index].get("name", ""))
        devices.append(
            InputDevice(
                index=index,
                name=str(info.get("name", f"aygıt {index}")),
                channels=channels,
                default_sample_rate=float(info.get("default_samplerate", 0.0)),
                is_default=(index == default_index),
                host_api=api_name,
            )
        )
    return devices


def resolve_device(value: str | int | None) -> int | None:
    """Kullanıcının verdiği değeri aygıt indeksine çevirir.

    `None` → işletim sisteminin varsayılanı (sounddevice'a None geçilir).
    Sayı → doğrudan indeks. Metin → adında geçen tek aygıt; birden fazla eşleşme
    varsa hata verilir, çünkü yanlış aygıttan sessiz kayıt almak en kötü sonuç.
    """
    if value is None or value == "":
        return None

    devices = list_input_devices()
    if not devices:
        raise AudioError("Hiç giriş aygıtı bulunamadı. Mikrofon bağlı mı?")

    text = str(value).strip()
    if text.lstrip("-").isdigit():
        index = int(text)
        if not any(d.index == index for d in devices):
            mevcut = ", ".join(str(d.index) for d in devices)
            raise AudioError(f"Giriş aygıtı {index} yok. Mevcut indeksler: {mevcut}")
        return index

    aday = [d for d in devices if text.casefold() in d.name.casefold()]
    if not aday:
        raise AudioError(f"'{text}' adında bir giriş aygıtı yok. Listelemek için: voxflow devices")
    if len(aday) > 1:
        eslesen = "; ".join(f"{d.index}={d.name}" for d in aday)
        raise AudioError(f"'{text}' birden fazla aygıta uyuyor: {eslesen}. İndeks verin.")
    return aday[0].index
