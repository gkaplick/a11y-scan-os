"""BITV 9.1.1.1d — Alternativen für CAPTCHAs.

CAPTCHAs, die nur eine Lösung zulassen, brauchen laut bitvtest-Prüfschritt
eine Alternative für andere Nutzergruppen (z. B. Audio-CAPTCHA) und eine
Beschreibung des Zwecks. Der Check arbeitet heuristisch:

- CAPTCHA-Grafiken werden über den Begriff „captcha/recaptcha“ in id, class,
  src, alt, aria-label, name oder placeholder erkannt.
- Jede erkannte <img>/<canvas>-Grafik braucht einen nicht-leeren
  Alternativtext, der den Zweck beschreibt (captcha, sicherheits-, zeichen-,
  code- oder eingabe-Bezug).
- Die Seite muss eine Alternative bereitstellen: ein <audio>-Element oder
  einen Link auf eine Hörversion.

Reine Text-CAPTCHAs (Mathe-/Logikfragen) sind ohne Künstliche Intelligenz
nicht von gewöhnlichem Text unterscheidbar und bleiben der manuellen
Prüfung überlassen (dokumentierte Grenze).
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_1_1_1d_ALTERNATIVEN_FUER_CAPTCHAS"

_CAPTCHA = re.compile(r"captcha|recaptcha", re.IGNORECASE)
_ZWECK = re.compile(
    r"captcha|sicherheit|zeichen|code|eingab|überprüf|ueberpruef", re.IGNORECASE
)
_AUDIO_ALT = re.compile(r"audio|hör|hoer|ansage|vorles", re.IGNORECASE)


def _captcha_hinweis(el) -> str:
    """Alle captcha-relevanten Textquellen eines Elements."""
    return " ".join(filter(None, (
        el.get("id"),
        " ".join(el.get("class") or []),
        el.get("src"),
        el.get("alt"),
        el.get("aria-label"),
        el.get("name"),
        el.get("placeholder"),
    )))


def _seite_hat_audio_alternative(soup) -> bool:
    if soup.find("audio") is not None:
        return True
    return any(
        _AUDIO_ALT.search(" ".join(filter(None, (
            a.get_text(strip=True), a.get("aria-label"), a.get("title"),
        ))))
        for a in soup.find_all("a", href=True)
    )


async def check_alternativen_fuer_captchas(ctx: CheckContext):
    """BITV 9.1.1.1d — CAPTCHA-Grafik ohne Alternativtext/Alternative."""
    errors = []
    grafiken = []
    for el in ctx.soup.find_all(["img", "canvas", "input"]):
        if not is_accessible_element(el):
            continue
        if _CAPTCHA.search(_captcha_hinweis(el)):
            if el.name in ("img", "canvas"):
                grafiken.append(el)

    if not grafiken:
        return []

    audio_alternative = _seite_hat_audio_alternative(ctx.soup)
    for el in grafiken:
        if el.name == "img":
            alt = (el.get("alt") or "").strip()
            if not alt:
                errors.append(finding(
                    _TEST_ID,
                    "CAPTCHA-Grafik ohne Alternativtext",
                    get_dom_path(el),
                ))
                continue
            if not _ZWECK.search(alt):
                errors.append(finding(
                    _TEST_ID,
                    f"CAPTCHA-Alternativtext ohne Zweckbeschreibung: „{alt}“",
                    get_dom_path(el),
                ))
        if not audio_alternative:
            errors.append(finding(
                _TEST_ID,
                "CAPTCHA ohne Audio-Alternative (keine Hörversion auf der Seite)",
                get_dom_path(el),
            ))
    return errors
