"""Kurallı (regex/anahtar sözcük) Türkçe niyet yorumlayıcı — NLU baseline.

Bu adaptör, LLM olmadan çalışan güvenilir taban çizgisidir. Qwen adaptörü ile
aynı IntentResult sözleşmesini üretir; böylece ikisi aynı test kümesinde
karşılaştırılabilir (experiments/nlu).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date

from voice_assistant.domain.dialogue import DialogueState
from voice_assistant.domain.schemas import Intent, IntentResult
from voice_assistant.services.dates import find_date
from voice_assistant.services.text_utils import normalize

CANCEL_WORDS = ("iptal", "vazgeç", "vazgeçtim", "boşver", "boş ver", "kapat şunu", "unut")
AFFIRM_WORDS = ("evet", "onaylıyorum", "onayla", "tamam", "olur", "kesinlikle", "sil gitsin")
DENY_WORDS = ("hayır", "hayir", "yok", "istemiyorum", "olmaz", "silme", "dur")

# Anlaşılan ama ilk sürümde bilinçli olarak desteklenmeyen istekler.
UNSUPPORTED_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bgörev(i|ini|leri|lerini|imi)?\s+(sil|kaldır|temizle)", "görev silme"),
    (r"\bnot(u|unu|ları|larımı|umu)?\s+(sil|kaldır|temizle)", "not silme"),
    (r"\b(tamamla|tamamlandı|bitti olarak|işaretle)", "görev tamamlama"),
    (r"\b(düzenle|değiştir|güncelle)\b", "görev/not düzenleme"),
    (r"\b(müzik|şarkı)\s+(çal|aç|başlat)", "müzik çalma"),
    (r"\b(e-?posta|mail|mesaj)\s+(gönder|yaz|at)", "e-posta/mesaj gönderme"),
    (r"\bhava\s+(durumu|nasıl)", "hava durumu sorgusu"),
    (r"\b(saat kaç|tarih ne)", "saat/tarih sorgusu"),
    (r"\b(bilgisayarı|sistemi)\s+(kapat|yeniden başlat)", "bilgisayarı kapatma"),
    (r"\b(dosya|klasör)\s+(sil|oluştur|taşı)", "dosya işlemleri"),
    (r"\b(komut|terminal(de)?)\s+(çalıştır|yaz)", "serbest komut çalıştırma"),
)

_TASK_RE = re.compile(
    r"^(?:bana\s+)?(?:yeni\s+)?(?:bir\s+)?görev\s+(?:ekle|oluştur|kaydet|aç|yaz)(?:\s*[:,]?\s*(?P<rest>.*))?$"
)
_TASK_SUFFIX_RE = re.compile(
    r"^(?P<rest>.+?)\s+(?:diye|adında|adlı|için|başlıklı)\s+(?:bir\s+)?görev\s+(?:ekle|oluştur|kaydet|yaz)$"
)
_TASK_SUFFIX2_RE = re.compile(r"^(?P<rest>.+?)\s+görevi(?:ni)?\s+(?:ekle|oluştur|kaydet)$")
_REMIND_RE = re.compile(r"^(?:bana\s+)?(?P<rest>.+?)\s*(?:'?[yn]?[iıuü])?\s+hatırlat$")
_NOTE_RE = re.compile(
    r"^(?:bana\s+)?(?:yeni\s+)?(?:bir\s+)?not\s+(?:al|ekle|oluştur|kaydet|yaz|tut)(?:\s*[:,]?\s*(?P<rest>.*))?$"
)
_NOTE_SUFFIX_RE = re.compile(
    r"^(?P<rest>.+?)\s+(?:diye|şeklinde|olarak)\s+(?:bir\s+)?not\s+(?:al|ekle|oluştur|kaydet|yaz|tut)$"
)
_NOTE_SUFFIX2_RE = re.compile(r"^(?P<rest>.+?)\s+notu(?:nu)?\s+(?:al|ekle|oluştur|kaydet)$")
_LIST_TASKS_RE = re.compile(
    r"(görev(ler)?(im)?(i|ı)?\s+(listele|göster|say|oku|neler|nelerdir|var mı|neymiş))"
    r"|(görevler(im)?\s*(ne(ler)?|neydi)?\s*$)|(^görevlerim$)|(hangi görevler(im)? var)"
    r"|(yapılacaklar(ı|ım)?\s+(listele|göster|neler))|(^yapılacaklar(ım)?$)"
)
_SHOW_HISTORY_RE = re.compile(
    r"geçmiş(i|imi)?\s+(göster|listele|oku|aç)|(son\s+)?komutlar(ım)?(ı)?\s+(göster|listele)"
)
_CLEAR_HISTORY_RE = re.compile(r"geçmiş(i|imi)?\s+(sil|temizle|kaldır)")
_OPEN_RE = re.compile(
    r"^(?P<target>.+?)\s*(?:'?[yn]?[iıuü])?\s+"
    r"(?:uygulamasını\s+|sitesini\s+|web sitesini\s+|sayfasını\s+|programını\s+)?"
    r"(?:aç|başlat|çalıştır|gir)(?:ar mısın|abilir misin|sana)?$"
)
_OPEN_PREFIX_RE = re.compile(r"^(?:aç|başlat)\s+(?P<target>.+)$")

TASK_FILLER_WORDS = ("görevi", "görevini", "diye", "adında", "adlı", "için", "başlıklı")


class RuleBasedInterpreter:
    """Belirleyici, hızlı, çevrimdışı niyet yorumlayıcı."""

    def __init__(
        self,
        app_aliases: dict[str, Iterable[str]] | None = None,
        site_aliases: dict[str, Iterable[str]] | None = None,
        today_provider: object | None = None,
    ) -> None:
        self._apps = {k: [normalize(a) for a in v] for k, v in (app_aliases or {}).items()}
        self._sites = {k: [normalize(a) for a in v] for k, v in (site_aliases or {}).items()}
        self._today = today_provider or date.today

    @property
    def name(self) -> str:
        return "rule_based"

    # ------------------------------------------------------------------ public
    def interpret(self, text: str, state: DialogueState) -> IntentResult:
        raw = text
        t = normalize(text)
        today: date = self._today()  # type: ignore[operator]

        if not t:
            return self._res(
                Intent.UNKNOWN, raw, question="Bir şey duyamadım. Ne yapmamı istersiniz?"
            )

        if self._matches_any(t, CANCEL_WORDS):
            return self._res(Intent.CANCEL, raw)

        # Onay/ret yalnızca bekleyen onay varsa anlamlıdır.
        if state.pending_confirmation is not None:
            if self._matches_any(t, AFFIRM_WORDS):
                return self._res(Intent.AFFIRM, raw)
            if self._matches_any(t, DENY_WORDS):
                return self._res(Intent.DENY, raw)

        # Eksik parametre bekleniyorsa, kullanıcı metni doğrudan o parametrenin değeri olabilir.
        if state.pending_action is not None:
            filled = self._fill_pending(t, raw, state, today)
            if filled is not None:
                return filled

        for pattern, label in UNSUPPORTED_PATTERNS:
            if re.search(pattern, t):
                return self._res(Intent.UNSUPPORTED, raw, params={"requested": label})

        if _CLEAR_HISTORY_RE.search(t):
            return self._res(Intent.CLEAR_HISTORY, raw)
        if _SHOW_HISTORY_RE.search(t):
            return self._res(Intent.SHOW_HISTORY, raw)
        if _LIST_TASKS_RE.search(t):
            params: dict[str, object] = {}
            dm = find_date(t, today)
            if dm:
                params["date"] = dm.value.isoformat()
            return self._res(Intent.LIST_TASKS, raw, params=params)

        task = self._parse_task(t, raw, today)
        if task:
            return task
        note = self._parse_note(t, raw)
        if note:
            return note
        opened = self._parse_open(t, raw)
        if opened:
            return opened

        return self._res(
            Intent.UNKNOWN,
            raw,
            question="Bunu anlayamadım. Örnek: 'görev ekle', 'not al', 'görevleri listele', "
            "'firefox aç'.",
        )

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _matches_any(t: str, words: Iterable[str]) -> bool:
        return any(re.search(rf"(^|\s){re.escape(w)}(\s|$)", t) for w in words)

    def _res(
        self,
        intent: Intent,
        raw: str,
        params: dict[str, object] | None = None,
        question: str | None = None,
        needs_clarification: bool = False,
    ) -> IntentResult:
        return IntentResult(
            intent=intent,
            parameters=dict(params or {}),
            needs_clarification=needs_clarification
            or question is not None
            and intent
            in (Intent.CREATE_TASK, Intent.CREATE_NOTE, Intent.OPEN_APP, Intent.OPEN_WEBSITE),
            clarification_question=question,
            confidence=1.0 if intent not in (Intent.UNKNOWN,) else 0.0,
            provider=self.name,
            raw_text=raw,
        )

    def _fill_pending(
        self, t: str, raw: str, state: DialogueState, today: date
    ) -> IntentResult | None:
        pending = state.pending_action
        assert pending is not None
        # Kullanıcı bekleyen işlem yerine başka net bir komut verdiyse ona öncelik tanınır.
        if self._looks_like_command(t):
            return None
        params = dict(pending.parameters)
        if pending.missing_parameter == "title":
            dm = find_date(t, today)
            title = self._strip_span(t, dm.span if dm else None)
            title = self._clean_title(title)
            if dm and "date" not in params:
                params["date"] = dm.value.isoformat()
            if not title:
                return None
            params["title"] = raw.strip() if not dm else title
            return self._res(pending.intent, raw, params=params)
        if pending.missing_parameter == "content":
            params["content"] = raw.strip()
            return self._res(pending.intent, raw, params=params)
        if pending.missing_parameter in ("app", "site"):
            key = self._lookup(t, self._apps if pending.missing_parameter == "app" else self._sites)
            if key is None:
                return None
            params[pending.missing_parameter] = key
            return self._res(pending.intent, raw, params=params)
        return None

    def _looks_like_command(self, t: str) -> bool:
        return bool(
            _TASK_RE.match(t)
            or _NOTE_RE.match(t)
            or _LIST_TASKS_RE.search(t)
            or _SHOW_HISTORY_RE.search(t)
            or _CLEAR_HISTORY_RE.search(t)
        )

    @staticmethod
    def _strip_span(t: str, span: tuple[int, int] | None) -> str:
        if span is None:
            return t
        return (t[: span[0]] + " " + t[span[1] :]).strip()

    @staticmethod
    def _clean_title(title: str) -> str:
        title = re.sub(r"\s+", " ", title).strip(" ,:")
        title = re.sub(r"^(bana|lütfen|bir|yeni)\s+", "", title)
        for w in TASK_FILLER_WORDS:
            title = re.sub(rf"(^|\s){w}(\s|$)", " ", title)
        title = re.sub(r"\b(için|tarihli|tarihinde|günü)\b$", "", title).strip(" ,:")
        return re.sub(r"\s+", " ", title).strip()

    def _parse_task(self, t: str, raw: str, today: date) -> IntentResult | None:
        m = _TASK_RE.match(t) or _TASK_SUFFIX_RE.match(t) or _TASK_SUFFIX2_RE.match(t)
        if not m and t.endswith("hatırlat"):
            m = _REMIND_RE.match(t)
        if not m:
            return None
        rest = (m.group("rest") or "").strip()
        params: dict[str, object] = {}
        dm = find_date(rest, today)
        if dm:
            params["date"] = dm.value.isoformat()
            rest = self._strip_span(rest, dm.span)
        title = self._clean_title(rest)
        if not title:
            return self._res(
                Intent.CREATE_TASK,
                raw,
                params=params,
                question="Görevin adı ne olsun?",
                needs_clarification=True,
            )
        params["title"] = title
        return self._res(Intent.CREATE_TASK, raw, params=params)

    def _parse_note(self, t: str, raw: str) -> IntentResult | None:
        m = _NOTE_RE.match(t) or _NOTE_SUFFIX_RE.match(t) or _NOTE_SUFFIX2_RE.match(t)
        if not m:
            return None
        rest = (m.group("rest") or "").strip(" ,:")
        if not rest:
            return self._res(
                Intent.CREATE_NOTE,
                raw,
                question="Not içeriği ne olsun?",
                needs_clarification=True,
            )
        return self._res(Intent.CREATE_NOTE, raw, params={"content": rest})

    def _parse_open(self, t: str, raw: str) -> IntentResult | None:
        m = _OPEN_RE.match(t) or _OPEN_PREFIX_RE.match(t)
        if not m:
            return None
        target = m.group("target").strip()
        target = re.sub(r"^(bana\s+|lütfen\s+|bir\s+)", "", target)
        app = self._lookup(target, self._apps)
        if app:
            return self._res(Intent.OPEN_APP, raw, params={"app": app})
        site = self._lookup(target, self._sites)
        if site:
            return self._res(Intent.OPEN_WEBSITE, raw, params={"site": site})
        # "aç" anlaşıldı ama hedef izin listesinde değil
        if re.search(r"\b(site|sitesi|web|sayfa)", t):
            intent = Intent.OPEN_WEBSITE
            key = "site"
        else:
            intent = Intent.OPEN_APP
            key = "app"
        return self._res(
            intent,
            raw,
            params={f"requested_{key}": target},
            question=f"'{target}' izin verilen "
            f"{'siteler' if key == 'site' else 'uygulamalar'} arasında değil. "
            + self._allowed_hint(key),
            needs_clarification=True,
        )

    def _allowed_hint(self, key: str) -> str:
        names = sorted(self._sites if key == "site" else self._apps)
        return "İzinli olanlar: " + ", ".join(names) if names else "İzin listesi boş."

    def _lookup(self, target: str, table: dict[str, list[str]]) -> str | None:
        target_n = normalize(target)
        # Türkçe belirtme eki temizliği: "youtube u", "firefox u", "hesap makinesini"
        candidates = {target_n, re.sub(r"\s+[yn]?[iıuü]$", "", target_n)}
        candidates.add(re.sub(r"(s)?[iıuü]n[iıuü]$", "", target_n))
        candidates.add(re.sub(r"[yn]?[iıuü]$", "", target_n))
        for key, aliases in table.items():
            for alias in aliases:
                if alias in candidates:
                    return key
        # Alias metnin tamamına eşit değil ama metin içinde geçiyorsa (örn. "bana firefox")
        for key, aliases in table.items():
            for alias in aliases:
                if re.search(rf"(^|\s){re.escape(alias)}(\s|$|['’])", target_n):
                    return key
        return None
