"""BITV 4 — Gebärdensprach-Video auf der Startseite.

§4 BITV 2.0: Öffentliche Stellen stellen die wichtigsten Inhalte ihres
Angebots auch in Deutscher Gebärdensprache (DGS) bereit — als Video — und
machen das Angebot erreichbar (Verlinkung, üblicherweise im Footer).

Geprüft wird, ob die Seite einen Link (a/area) oder ein Video enthält,
dessen Beschriftung auf ein Gebärdensprach-Angebot verweist. Eine Seite, die
selbst das Gebärdensprach-Angebot ist (Titel), löst keinen Befund aus.

Erkennung bewusst über den zugänglichen Namen (Text/aria-label/title) statt
über die Ziel-URL: Ein Angebot wird über die Beschriftung des Links
kommuniziert, nicht über den Pfad — und eine URL, die zufällig einen
Gebärdensprach-Begriff enthält (z. B. eine Unterseite, deren Pfad den
Begriff führt), wäre ein False-Positive. Die inhaltliche Qualität und
Aktualität des Videos sind statisch nicht prüfbar — dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, is_accessible_element

_TEST_ID = "BITV_4_SIGN_LANGUAGE"

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
    """BITV 4 — Seite verlinkt kein Gebärdensprach-Angebot."""
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
        "Gebärdensprach-Video (DGS) bereitstellen und von jeder Seite "
        "erreichbar verlinken",
        "body",
    )]
