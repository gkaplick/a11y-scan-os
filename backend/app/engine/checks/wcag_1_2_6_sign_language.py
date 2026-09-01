"""WCAG 1.2.6 — Gebärdensprache (voraufgezeichnet, AAA).

Gleiche Regel wie BITV 4 (§4-Angebot): Voraufgezeichnete Medien brauchen
eine Gebärdensprach-Übersetzung (DGS). Erkannt wird, ob die Seite ein
Gebärdensprach-Angebot bereitstellt — einen Link (a/area) oder ein Video,
dessen Beschriftung auf Gebärdensprache verweist. Eine Seite, die selbst das
Gebärdensprach-Angebot ist (Titel), löst keinen Befund aus.

Anwendbarkeits-Gate: Das Kriterium betrifft nur Seiten mit voraufgezeichnetem
Video — ohne `<video>` ist es nicht anwendbar und wird nicht gemeldet
(anders als das BITV-4-Angebot, das auf jeder Seite erreichbar sein muss).

Erkennung bewusst über den zugänglichen Namen (Text/aria-label/title) statt
über die Ziel-URL: Ein Angebot wird über die Beschriftung des Links
kommuniziert, nicht über den Pfad — und eine URL, die zufällig einen
Gebärdensprach-Begriff enthält, wäre ein False-Positive. Die inhaltliche
Qualität und Aktualität der Übersetzung sind statisch nicht prüfbar —
dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, is_accessible_element

_TEST_ID = "WCAG_1_2_6_SIGN_LANGUAGE"

# Linktext/-ziel bzw. Video-Beschriftung weist auf ein Gebärdensprach-Angebot
_SIGN_LINK = re.compile(
    r"gebärden|gebarden|gebaerden|sign\s?language|signlang|\bdgs\b",
    re.IGNORECASE,
)
_SIGN_PAGE = _SIGN_LINK  # dieselben Begriffe kennzeichnen auch die Angebotsseite


def _beschriftung(el) -> str:
    return " ".join(filter(None, (
        el.get_text(strip=True),
        el.get("aria-label"),
        el.get("title"),
    )))


async def check_sign_language(ctx: CheckContext):
    """WCAG 1.2.6 — Voraufgezeichnetes Video ohne Gebärdensprach-Übersetzung."""
    if not ctx.soup.find("video"):
        return []  # kein voraufgezeichnetes Medium → nicht anwendbar

    title = ctx.soup.title.get_text() if ctx.soup.title else ""
    if _SIGN_PAGE.search(title):
        return []

    for el in ctx.soup.find_all(["a", "area"], href=True):
        if not is_accessible_element(el):
            continue
        if _SIGN_LINK.search(_beschriftung(el)):
            return []

    for vid in ctx.soup.find_all("video"):
        if not is_accessible_element(vid):
            continue
        if _SIGN_LINK.search(_beschriftung(vid)):
            return []

    return [finding(
        _TEST_ID,
        "Kein verlinktes Gebärdensprach-Angebot gefunden — "
        "Gebärdensprach-Video (DGS) für die voraufgezeichneten Medien "
        "bereitstellen und von jeder Seite erreichbar verlinken",
        "body",
    )]
