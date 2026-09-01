"""BITV 7 — Erklärung zur Barrierefreiheit.

BITV 2.0 §7 / §12 BGG: Öffentliche Stellen veröffentlichen eine Erklärung zur
Barrierefreiheit und machen sie von allen Seiten des Angebots erreichbar
(üblicherweise per Footer-Link).

Geprüft wird, ob die Seite einen Link (a/area) enthält, dessen Beschriftung
oder Ziel auf die Erklärung verweist (inkl. englischer „accessibility
statement"-Varianten). Eine Seite, die selbst die Erklärung ist (Titel oder
Überschrift enthalten „Erklärung zur Barrierefreiheit"), löst keinen Befund
aus. Die inhaltlichen Pflichtfelder der Erklärung sind statisch nicht prüfbar
— dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, is_accessible_element

_TEST_ID = "BITV_7_DECLARATION"

# Linktext/-ziel weist auf die Barrierefreiheits-Erklärung
_DECL_LINK = re.compile(
    r"erklärung.{0,20}barrierefrei|barrierefreiheits?erklärung|"
    r"accessibility statement|barrierefreiheit",
    re.IGNORECASE,
)
# Seite IST selbst die Erklärung
_DECL_PAGE = re.compile(
    r"erklärung.{0,20}barrierefrei|barrierefreiheits?erklärung|accessibility statement",
    re.IGNORECASE,
)


def _link_text(el) -> str:
    return " ".join(filter(None, (
        el.get_text(strip=True),
        el.get("aria-label"),
        el.get("title"),
    )))


async def check_declaration_link(ctx: CheckContext):
    """BITV 7 — Seite verlinkt die Erklärung zur Barrierefreiheit nicht."""
    # Die Erklärungs-Seite selbst ist erfüllt (kein externer Verweis nötig).
    # Nur der Dokumenttitel zählt — Überschriften können den Katalog-Begriff
    # als Themenbezug tragen, ohne dass die Seite die Erklärung ist.
    title = ctx.soup.title.get_text() if ctx.soup.title else ""
    if _DECL_PAGE.search(title):
        return []

    for el in ctx.soup.find_all(["a", "area"], href=True):
        if not is_accessible_element(el):
            continue
        if _DECL_LINK.search(_link_text(el)) or _DECL_LINK.search(el.get("href", "")):
            return []

    return [finding(
        _TEST_ID,
        "Keine verlinkte Erklärung zur Barrierefreiheit gefunden — "
        "von jeder Seite aus erreichbar verlinken (z. B. im Footer)",
        "body",
    )]
