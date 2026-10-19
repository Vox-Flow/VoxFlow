"""Terminal arayüzü.

Modlar:
  voxflow --text "görev ekle"      tek komut (metin)
  voxflow chat                     etkileşimli metin modu (ses/LLM gerekmez)
  voxflow listen                   Enter ile kaydı başlat/bitir -> ASR -> komut (Faz 2)
  voxflow info                     ortam/adaptör durumu
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from voice_assistant import __version__
from voice_assistant.domain.errors import AudioError, VoxFlowError
from voice_assistant.domain.schemas import ActionResult, ActionStatus
from voice_assistant.logging_setup import setup_logging
from voice_assistant.services.presenter import ConsolePresenter

PROMPT = "sen> "


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="voxflow", description="Yerel Türkçe sesli asistan (terminal)")
    p.add_argument("--version", action="version", version=f"voxflow {__version__}")
    p.add_argument("--config", type=Path, default=None, help="app.json yolu")
    p.add_argument("--data-dir", type=Path, default=None, help="not/görev/geçmiş JSON dizini")
    p.add_argument("--no-history", action="store_true", help="geçmişe yazma")
    p.add_argument("--log-level", default=None)
    p.add_argument(
        "--text",
        "-t",
        action="append",
        help="metin komut (birden çok verilebilir, sırayla işlenir)",
    )
    sub = p.add_subparsers(dest="command")
    sub.add_parser("chat", help="etkileşimli metin modu")
    sub.add_parser("listen", help="Enter ile ses kaydı -> ASR -> komut")
    sub.add_parser("info", help="ortam ve adaptör durumu")
    return p


def run_text(container, texts: list[str], presenter: ConsolePresenter) -> int:  # type: ignore[no-untyped-def]
    rc = 0
    for t in texts:
        presenter.status("komut doğrulanıyor")
        result = container.assistant.handle_text(t)
        presenter.show(result)
        if result.status == ActionStatus.ERROR:
            rc = 1
    return rc


def run_chat(container, presenter: ConsolePresenter) -> int:  # type: ignore[no-untyped-def]
    presenter.status("hazır — metin modu. Çıkmak için 'çık' veya Ctrl-D.")
    while True:
        try:
            line = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().lower() in {"çık", "cik", "exit", "quit", "q"}:
            break
        if not line.strip():
            continue
        presenter.show(container.assistant.handle_text(line))
    presenter.status("görüşürüz")
    return 0


def run_listen(container, presenter: ConsolePresenter) -> int:  # type: ignore[no-untyped-def]
    """Enter ile başlat / Enter ile bitir. Ham ses yalnızca bellekte tutulur."""
    rec = container.recognizer
    if not rec.is_available():
        presenter.show(
            ActionResult(
                status=ActionStatus.ERROR,
                message=f"ASR hazır değil ({rec.name}). config/app.json içinde asr.provider ve "
                "model kurulumunu kontrol edin; "
                "metin modu için 'voxflow chat' kullanabilirsiniz.",
                error_code="E_ASR_UNAVAILABLE",
            )
        )
        return 1
    try:
        from voice_assistant.adapters.audio.sounddevice_capture import SounddeviceCapture

        capture = SounddeviceCapture(
            container.config.audio.sample_rate,
            container.config.audio.channels,
            container.config.audio.max_seconds,
        )
    except AudioError as exc:
        presenter.show(
            ActionResult(status=ActionStatus.ERROR, message=exc.message, error_code=exc.code)
        )
        return 1

    presenter.status(f"hazır — ASR: {rec.name}. Kayıt için Enter, çıkmak için 'çık'.")
    try:
        while True:
            try:
                cmd = input("[Enter: kaydı başlat] ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if cmd.strip().lower() in {"çık", "cik", "exit", "quit", "q"}:
                break
            try:
                capture.start()
                presenter.status("kayıt alınıyor — bitirmek için Enter")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    capture.close()
                    presenter.status("iptal")
                    continue
                clip = capture.stop()
                presenter.status(f"ses çözümleniyor ({clip.duration_s:.1f} sn)")
                transcript = rec.transcribe(clip)
            except VoxFlowError as exc:
                presenter.show(
                    ActionResult(
                        status=ActionStatus.ERROR, message=exc.message, error_code=exc.code
                    )
                )
                continue
            finally:
                clip = None  # ham sese referans bırakma
            lat = f", {transcript.latency_s:.2f} sn" if transcript.latency_s is not None else ""
            print(f"sen (ASR{lat})> {transcript.text}")
            if not transcript.text.strip():
                presenter.show(
                    ActionResult(
                        status=ActionStatus.UNKNOWN, message="Konuşma algılanamadı. Tekrar deneyin."
                    )
                )
                continue
            presenter.status("komut doğrulanıyor")
            presenter.show(container.assistant.handle_text(transcript.text))
    finally:
        capture.close()
    return 0


def run_info(container, presenter: ConsolePresenter) -> int:  # type: ignore[no-untyped-def]
    c = container
    print(f"voxflow {__version__}")
    print(f"veri dizini : {c.store.data_dir}")
    print(f"NLU         : {c.assistant.interpreter.name}")
    print(f"ASR         : {c.recognizer.name} (hazır: {c.recognizer.is_available()})")
    print(
        f"TTS         : {c.tts.name} "
        f"(ses üretir: {c.tts.name != 'console' and c.tts.is_available()})"
    )
    print(f"platform    : {c.launcher.platform}")
    print(f"izinli uygulamalar: {', '.join(sorted(c.launcher.apps)) or '-'}")
    print(f"izinli siteler    : {', '.join(sorted(c.launcher.sites)) or '-'}")
    for w in c.warnings:
        print(f"uyarı: {w}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    setup_logging(args.log_level)
    from voice_assistant.wiring import build_container

    try:
        container = build_container(args.config, args.data_dir, record_history=not args.no_history)
    except VoxFlowError as exc:
        print(f"[✖ hata ({exc.code})] {exc.message}", file=sys.stderr)
        return 2
    presenter = ConsolePresenter(container.tts)
    if args.command not in ("info", "listen"):
        for w in container.warnings:
            if "ASR" in w and not args.command == "listen":
                continue
            print(f"[uyarı] {w}", file=sys.stderr)

    if args.text:
        return run_text(container, args.text, presenter)
    if args.command == "chat" or args.command is None:
        return run_chat(container, presenter)
    if args.command == "listen":
        return run_listen(container, presenter)
    if args.command == "info":
        return run_info(container, presenter)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
