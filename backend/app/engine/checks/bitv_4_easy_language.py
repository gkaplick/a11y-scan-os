"""BITV 4 — Leichte-Sprache-Angebot auf der Startseite.

§4 BITV 2.0: Öffentliche Stellen stellen die wichtigsten Inhalte ihres
Angebots auch in Leichter Sprache bereit und machen das Angebot erreichbar
(Verlinkung, üblicherweise im Footer).

Geprüft wird, ob die Seite einen Link (a/area) enthält, dessen Beschriftung
auf ein Leichte-Sprache-Angebot verweist. Eine Seite, die selbst das
Leichte-Sprache-Angebot ist (Titel), löst keinen Befund aus.

Erkennung bewusst über den zugänglichen Namen (Text/aria-label/title) statt
über die Ziel-URL: Ein Angebot wird über die Beschriftung des Links
kommuniziert, nicht über den Pfad — und eine URL, die zufällig einen
Leichte-Sprache-Begriff enthält (z. B. eine Unterseite, deren Pfad den
Begriff führt), wäre ein False-Positive. Die inhaltliche Korrektheit der
Leichten Sprache ist statisch nicht prüfbar — dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, is_accessible_element

_TEST_ID = "BITV_4_EASY_LANGUAGE"

# Linktext/-ziel weist auf ein Leichte-Sprache-Angebot (inkl. gängiger
# Synonyme und Transliterationen; Leichte und Einfache Sprache werden
# in der Erkennung gleich behandelt).
_EASY_LINK = re.compile(
    r"leicht[een]?\s*[-–]?\s*sprache|leicht\s?lesbar|"
    r"easy\s*(to\s*)?read|einfache\s*sprache|easylang",
    re.IGNORECASE,
)
_EASY_PAGE = _EASY_LINK


def _beschriftung(el) -> str:
    return " ".join(filter(None, (
        el.get_text(strip=True),
        el.get("aria-label"),
        el.get("title"),
    )))


async def check_easy_language(ctx: CheckContext):
    """BITV 4 — Seite verlinkt kein Leichte-Sprache-Angebot."""
    title = ctx.soup.title.get_text() if ctx.soup.title else ""
    if _EASY_PAGE.search(title):
        return []

    for el in ctx.soup.find_all(["a", "area"], href=True):
        if not is_accessible_element(el):
            continue
        if _EASY_LINK.search(_beschriftung(el)):
            return []

    return [finding(
        _TEST_ID,
        "Kein verlinktes Leichte-Sprache-Angebot gefunden — "
        "Version in Leichter Sprache bereitstellen und von jeder Seite "
        "erreichbar verlinken",
        "body",
    )]
