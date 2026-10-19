from datetime import date

import pytest

from voice_assistant.services.dates import find_date, parse_iso_date

TODAY = date(2026, 10, 19)  # Pazartesi


@pytest.mark.parametrize(
    "text, expected",
    [
        ("bugün", date(2026, 10, 19)),
        ("yarın matematik", date(2026, 10, 20)),
        ("öbür gün", date(2026, 10, 21)),
        ("3 gün sonra", date(2026, 10, 22)),
        ("iki gün sonra", date(2026, 10, 21)),
        ("cuma", date(2026, 10, 23)),
        ("pazartesi", date(2026, 10, 26)),  # bugün pazartesi -> gelecek pazartesi
        ("gelecek cuma", date(2026, 10, 30)),
        ("haftaya salı", date(2026, 10, 27)),
        ("20 ekim", date(2026, 10, 20)),
        ("5 ocak", date(2027, 1, 5)),  # geçmişse gelecek yıl
        ("20 ekim 2027", date(2027, 10, 20)),
        ("2026-11-01", date(2026, 11, 1)),
        ("25.12.2026", date(2026, 12, 25)),
        ("1/11", date(2026, 11, 1)),
        ("haftaya", date(2026, 10, 26)),
    ],
)
def test_find_date(text: str, expected: date) -> None:
    m = find_date(text, TODAY)
    assert m is not None, text
    assert m.value == expected


@pytest.mark.parametrize("text", ["matematik ödevi", "", "31 şubat", "bir şey"])
def test_find_date_none(text: str) -> None:
    assert find_date(text, TODAY) is None


def test_parse_iso_date() -> None:
    assert parse_iso_date("2026-10-20") == date(2026, 10, 20)
    assert parse_iso_date("2026-13-20") is None
    assert parse_iso_date("yarın") is None
