"""CLI --text modu: gerçek JsonStore, gerçek config örnekleri; uygulama/URL açma mock."""

import json

import pytest

from voice_assistant import cli


@pytest.fixture
def no_real_launch(monkeypatch):  # type: ignore[no-untyped-def]
    from voice_assistant.adapters.platforms import launcher as mod

    calls: dict[str, list] = {"spawn": [], "url": []}
    monkeypatch.setattr(
        mod.AllowlistLauncher,
        "_default_spawn",
        staticmethod(lambda argv: calls["spawn"].append(tuple(argv))),
    )
    monkeypatch.setattr(mod.webbrowser, "open", lambda u, new=0: calls["url"].append(u) or True)
    return calls


def test_cli_text_task_flow(tmp_path, capsys, no_real_launch) -> None:  # type: ignore[no-untyped-def]
    rc = cli.main(
        ["--data-dir", str(tmp_path), "--text", "görev ekle", "--text", "Matematik ödevi"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "açıklama gerekli" in out and "Görev eklendi" in out
    data = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert data["items"][0]["title"] == "Matematik ödevi"


def test_cli_text_cancel_flow(tmp_path, capsys, no_real_launch) -> None:  # type: ignore[no-untyped-def]
    rc = cli.main(["--data-dir", str(tmp_path), "--text", "görev ekle", "--text", "vazgeçtim"])
    out = capsys.readouterr().out
    assert rc == 0 and "iptal" in out
    assert not (tmp_path / "tasks.json").exists()


def test_cli_open_site_is_mocked(tmp_path, capsys, no_real_launch) -> None:  # type: ignore[no-untyped-def]
    rc = cli.main(["--data-dir", str(tmp_path), "--text", "youtube aç"])
    assert rc == 0
    assert no_real_launch["url"] == ["https://www.youtube.com"]


def test_cli_info(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        cli.main(["--config", "config/app.example.json", "--data-dir", str(tmp_path), "info"]) == 0
    )
    out = capsys.readouterr().out
    assert "rule_based" in out and "mock" in out


def test_cli_record_rejects_empty_consent(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    """Açık izin olmadan kayıt başlamaz; kullanıcıya traceback değil hata kodu gösterilir."""
    rc = cli.main(
        [
            "--config",
            "config/app.example.json",
            "--data-dir",
            str(tmp_path),
            "record",
            "--speaker",
            "spk_01",
            "--split",
            "train",
            "--consent",
            "   ",
            "--audio-root",
            str(tmp_path / "audio"),
            "--manifest",
            str(tmp_path / "m.jsonl"),
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "E_VALIDATION" in err and "izin" in err
    assert not (tmp_path / "m.jsonl").exists()


def test_cli_record_summary_and_skip(tmp_path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Ses paketleri kurulu olmasa bile: cümleler atlanır, özet basılır, ses yazılmaz."""
    answers = iter(["a", "ç"])
    monkeypatch.setattr("builtins.input", lambda *a: next(answers))
    sentences = tmp_path / "s.md"
    sentences.write_text("- C001: görev ekle\n- C002: not al\n", encoding="utf-8")
    rc = cli.main(
        [
            "--config",
            "config/app.example.json",
            "--data-dir",
            str(tmp_path),
            "record",
            "--speaker",
            "spk_02",
            "--split",
            "val",
            "--consent",
            "team_consent_v1",
            "--sentences",
            str(sentences),
            "--audio-root",
            str(tmp_path / "audio"),
            "--manifest",
            str(tmp_path / "m.jsonl"),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert '"kaydedilen": 0' in out and '"toplam": 2' in out
    assert not list((tmp_path / "audio").rglob("*.wav"))


def test_cli_verify_missing_manifest(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    rc = cli.main(
        [
            "--config",
            "config/app.example.json",
            "--data-dir",
            str(tmp_path),
            "verify",
            "--manifest",
            str(tmp_path / "yok.jsonl"),
        ]
    )
    assert rc == 1
    assert "Manifest yok" in capsys.readouterr().out
