"""Terminal arayüzü.

Modlar:
  voxflow --text "görev ekle"      tek komut (metin)
  voxflow chat                     etkileşimli metin modu (ses/LLM gerekmez)
  voxflow listen                   Enter ile kaydı başlat/bitir -> ASR -> komut (Faz 2)
  voxflow info                     ortam/adaptör durumu
  voxflow record --speaker spk_01 --session s01 --split train --consent team_consent_v1
                                   veri toplama oturumu (araştırma; docs/dataset_protocol.md)
  voxflow verify --manifest ...    kaydedilen transkriptleri dinleyip onayla/düzelt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from voice_assistant import __version__
from voice_assistant.domain.errors import AudioError, VoxFlowError
from voice_assistant.domain.schemas import ActionResult, ActionStatus
from voice_assistant.logging_setup import setup_logging
from voice_assistant.services.presenter import ConsolePresenter

PROMPT = "sen> "
DEFAULT_SENTENCES = Path("docs/recording_sentences_tr.md")


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

    rec = sub.add_parser("record", help="veri toplama oturumu (gönüllü kaydı)")
    rec.add_argument("--speaker", required=True, help="anonim kod, örn. spk_01")
    rec.add_argument("--session", default="s01", help="oturum kodu, örn. s01")
    rec.add_argument("--split", required=True, choices=["train", "val", "test"])
    rec.add_argument(
        "--consent", required=True, help="örn. team_consent_v1 — açık izin alınmadan kayıt yok"
    )
    rec.add_argument("--sentences", type=Path, default=DEFAULT_SENTENCES)
    rec.add_argument("--audio-root", type=Path, default=Path("datasets/audio"))
    rec.add_argument("--manifest", type=Path, default=None, help="varsayılan: konuşmacıya göre")
    rec.add_argument("--environment", default="quiet", choices=["quiet", "noisy"])
    rec.add_argument("--device-note", default="", help="mikrofon/cihaz türü (seri numarası yazma)")
    rec.add_argument("--limit", type=int, default=None, help="bu oturumda en fazla N cümle")

    ver = sub.add_parser("verify", help="kayıtları dinleyip transkripti onayla/düzelt")
    ver.add_argument("--manifest", type=Path, required=True)
    ver.add_argument(
        "--sidecar", type=Path, default=None, help="varsayılan: ses dizininden bulunur"
    )
    ver.add_argument("--no-audio", action="store_true", help="ses çalma, yalnızca metin göster")
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


def run_record(args, presenter: ConsolePresenter) -> int:  # type: ignore[no-untyped-def]
    """Gönüllü kayıt oturumu. Ses yalnızca açık izinle ve yerel dizine yazılır."""
    from voice_assistant.services.recording import RecordingSession, load_sentences

    sentences = load_sentences(args.sentences)
    manifest = args.manifest or (Path("datasets/manifests") / f"asr_{args.speaker}_real.jsonl")
    session = RecordingSession(
        speaker_id=args.speaker,
        session_id=args.session,
        split=args.split,
        consent=args.consent,
        audio_root=args.audio_root,
        manifest_path=manifest,
        environment=args.environment,
        device=args.device_note,
    )
    pending = session.pending(sentences)
    if args.limit:
        pending = pending[: args.limit]
    if not pending:
        presenter.status("bu oturumda kaydedilecek cümle kalmadı")
        print(json.dumps(session.summary(sentences), ensure_ascii=False, indent=2))
        return 0

    try:
        from voice_assistant.adapters.audio.sounddevice_capture import SounddeviceCapture

        capture = SounddeviceCapture(session.sample_rate, 1, 60)
    except AudioError as exc:
        presenter.show(
            ActionResult(status=ActionStatus.ERROR, message=exc.message, error_code=exc.code)
        )
        return 1

    presenter.status(
        f"{args.speaker}/{args.session} — {len(pending)} cümle, {args.split}. "
        "Her cümlede: Enter kaydet, Enter bitir. Komutlar: a=atla, ç=çık"
    )
    done = 0
    try:
        for i, sentence in enumerate(pending, 1):
            while True:
                print(f"\n[{i}/{len(pending)}] {sentence.id}: {sentence.text}")
                cmd = input("[Enter: kaydet · a: atla · ç: çık] ").strip().lower()
                if cmd in {"ç", "c", "çık", "cik", "q"}:
                    raise KeyboardInterrupt
                if cmd in {"a", "atla"}:
                    break
                try:
                    capture.start()
                    presenter.status("kayıt alınıyor — bitirmek için Enter")
                    input()
                    clip = capture.stop()
                except AudioError as exc:
                    presenter.show(
                        ActionResult(
                            status=ActionStatus.ERROR, message=exc.message, error_code=exc.code
                        )
                    )
                    continue
                samples = list(clip.to_float32())  # type: ignore[call-overload]
                record = session.save(sentence, samples)
                done += 1
                flags = ", ".join(record["quality_flags"])  # type: ignore[arg-type]
                presenter.show(
                    ActionResult(
                        status=ActionStatus.SUCCESS,
                        message=f"{record['sample_id']} kaydedildi "
                        f"({record['duration_s']} sn, {flags})",
                    )
                )
                again = input("[Enter: sonraki · t: tekrar al] ").strip().lower()
                if again not in {"t", "tekrar"}:
                    break
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
        capture.close()
    presenter.status(f"oturum bitti — {done} kayıt eklendi")
    print(json.dumps(session.summary(sentences), ensure_ascii=False, indent=2))
    return 0


def run_verify(args, presenter: ConsolePresenter) -> int:  # type: ignore[no-untyped-def]
    """İnsan kontrolü turu: hedef metin ile gerçekten söylenen karşılaştırılır."""
    from voice_assistant.services.recording import (
        drop_sample,
        mark_verified,
        read_wav_pcm16,
        update_transcript,
    )

    if not args.manifest.exists():
        presenter.show(
            ActionResult(
                status=ActionStatus.ERROR,
                message=f"Manifest yok: {args.manifest}",
                error_code="E_VALIDATION",
            )
        )
        return 1
    records = [
        json.loads(line)
        for line in args.manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    play = None
    if not args.no_audio:
        try:
            import sounddevice as sd

            play = sd.play
        except ImportError:
            presenter.status("sounddevice yok — ses çalmadan, yalnızca metinle doğrulama")

    presenter.status(f"{len(records)} kayıt — Enter: doğru · d: düzelt · r: reddet · ç: çık")
    checked = 0
    for i, rec in enumerate(records, 1):
        path = Path(str(rec["audio_path"]))
        print(f"\n[{i}/{len(records)}] {rec['sample_id']}  ({rec['duration_s']} sn)")
        print(f"  hedef: {rec['transcript']}")
        if play is not None and path.exists():
            try:
                samples, rate = read_wav_pcm16(path)
                play(samples, rate)
            except Exception as exc:  # noqa: BLE001 - çalma hatası doğrulamayı durdurmaz
                print(f"  (ses çalınamadı: {exc})")
        elif not path.exists():
            print(f"  (ses dosyası yok: {path})")
        try:
            cmd = input("[Enter/d/r/ç] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if cmd in {"ç", "c", "q"}:
            break
        sidecar = args.sidecar or (path.parent / f"session_{rec['sample_id'].split('_')[1]}.csv")
        if cmd in {"r", "reddet"}:
            drop_sample(args.manifest, str(rec["sample_id"]))
            print("  reddedildi, ses silindi")
            continue
        if cmd in {"d", "düzelt", "duzelt"}:
            text = input("  gerçekten söylenen: ").strip()
            if text:
                update_transcript(args.manifest, str(rec["sample_id"]), text)
                print("  transkript güncellendi")
        mark_verified(sidecar, str(rec["sample_id"]))
        checked += 1
    presenter.status(f"doğrulanan kayıt: {checked}")
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


def _force_utf8_stdio() -> None:
    """Windows konsolu varsayılan olarak cp1252 kullanır; Türkçe karakterler çökmesin."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # kapalı/yönlendirilmiş akış
                pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
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

    try:
        if args.text:
            return run_text(container, args.text, presenter)
        if args.command == "chat" or args.command is None:
            return run_chat(container, presenter)
        if args.command == "listen":
            return run_listen(container, presenter)
        if args.command == "info":
            return run_info(container, presenter)
        if args.command == "record":
            return run_record(args, presenter)
        if args.command == "verify":
            return run_verify(args, presenter)
    except VoxFlowError as exc:  # kullanıcıya traceback değil, anlaşılır hata
        print(f"[✖ hata ({exc.code})] {exc.message}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
