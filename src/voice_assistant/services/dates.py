"""Türkçe göreli/mutlak tarih ifadelerini gerçek yerel tarihe göre çözer.

Kural: Çözülemeyen ifade için None döner; asla sessizce tahmin edilmez.
`today` parametresi testlerde deterministik sonuç için enjekte edilir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

WEEKDAYS: dict[str, int] = {
    "pazartesi": 0,
    "salı": 1,
    "sali": 1,
    "çarşamba": 2,
    "carsamba": 2,
    "perşembe": 3,
    "persembe": 3,
    "cuma": 4,
    "cumartesi": 5,
    "pazar": 6,
}
MONTHS: dict[str, int] = {
    "ocak": 1,
    "şubat": 2,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "agustos": 8,
    "eylül": 9,
    "eylul": 9,
    "ekim": 10,
    "kasım": 11,
    "kasim": 11,
    "aralık": 12,
    "aralik": 12,
}
NUMBER_WORDS: dict[str, int] = {
    "bir": 1,
    "iki": 2,
    "üç": 3,
    "uc": 3,
    "dört": 4,
    "dort": 4,
    "beş": 5,
    "bes": 5,
    "altı": 6,
    "alti": 6,
    "yedi": 7,
    "sekiz": 8,
    "dokuz": 9,
    "on": 10,
}


@dataclass(frozen=True)
class DateMatch:
    value: date
    span: tuple[int, int]  # metindeki konum; başlık çıkarımında kullanılır
    text: str


_RE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_RE_DMY = re.compile(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{4}))?\b")
_RE_DAY_MONTH = re.compile(
    r"\b(\d{1,2})\s+("
    + "|".join(sorted(MONTHS, key=len, reverse=True))
    + r")(?:\s+(\d{4}))?(?:'?[a-zğüşıöç]*)?\b"
)
_RE_N_DAYS = re.compile(r"\b(\d+|" + "|".join(NUMBER_WORDS) + r")\s+gün\s+sonra\b")
_RE_WEEKDAY = re.compile(
    r"\b(gelecek|önümüzdeki|haftaya|bu)?\s*("
    + "|".join(sorted(WEEKDAYS, key=len, reverse=True))
    + r")(?:\s+günü)?(?:'?[a-zğüşıöç]*)?\b"
)
_RELATIVE: dict[str, int] = {
    "bugün": 0,
    "bugun": 0,
    "yarın": 1,
    "yarin": 1,
    "öbür gün": 2,
    "obur gun": 2,
    "ertesi gün": 2,
    "yarından sonra": 2,
    "haftaya": 7,
    "gelecek hafta": 7,
    "önümüzdeki hafta": 7,
}


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def find_date(text: str, today: date | None = None) -> DateMatch | None:
    """Metindeki ilk tarih ifadesini bulur. Bulamazsa None."""
    today = today or date.today()
    low = text.lower()

    m = _RE_ISO.search(low)
    if m:
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            return DateMatch(d, m.span(), m.group(0))

    m = _RE_DAY_MONTH.search(low)
    if m:
        year = int(m.group(3)) if m.group(3) else today.year
        d = _safe_date(year, MONTHS[m.group(2)], int(m.group(1)))
        if d:
            if not m.group(3) and d < today:
                d = _safe_date(year + 1, d.month, d.day) or d
            return DateMatch(d, m.span(), m.group(0))

    m = _RE_DMY.search(low)
    if m:
        year = int(m.group(3)) if m.group(3) else today.year
        d = _safe_date(year, int(m.group(2)), int(m.group(1)))
        if d:
            if not m.group(3) and d < today:
                d = _safe_date(year + 1, d.month, d.day) or d
            return DateMatch(d, m.span(), m.group(0))

    m = _RE_N_DAYS.search(low)
    if m:
        tok = m.group(1)
        n = int(tok) if tok.isdigit() else NUMBER_WORDS[tok]
        return DateMatch(today + timedelta(days=n), m.span(), m.group(0))

    # Uzun ifadeler önce ("öbür gün" > "bugün" çakışması için)
    for phrase in sorted(_RELATIVE, key=len, reverse=True):
        idx = low.find(phrase)
        if idx != -1:
            # "haftaya pazartesi" gibi haftagünü içeren ifadeleri aşağıya bırak
            if phrase in {"haftaya", "gelecek hafta", "önümüzdeki hafta"} and _RE_WEEKDAY.search(
                low
            ):
                break
            return DateMatch(
                today + timedelta(days=_RELATIVE[phrase]), (idx, idx + len(phrase)), phrase
            )

    m = _RE_WEEKDAY.search(low)
    if m:
        qualifier, day_name = m.group(1), m.group(2)
        target = WEEKDAYS[day_name]
        delta = (target - today.weekday()) % 7
        if delta == 0:
            delta = 7  # "pazartesi" bugünse bir sonraki pazartesi kastedilir
        if qualifier in {"gelecek", "önümüzdeki", "haftaya"} and delta < 7:
            # Bu haftanın o günü henüz gelmediyse de "gelecek X" bir sonraki haftayı kasteder
            delta += 7
        return DateMatch(today + timedelta(days=delta), m.span(), m.group(0))

    return None


def parse_iso_date(value: str) -> date | None:
    """LLM/konfig kaynaklı 'YYYY-MM-DD' metnini doğrular. Geçersizse None."""
    m = _RE_ISO.fullmatch(value.strip())
    if not m:
        return None
    return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
