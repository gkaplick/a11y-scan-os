"""BITV_9_1_3_1b_HTML_STRUKTURELEMENTE_FUER_LISTEN — HTML-Strukturelemente für Listen.

Prüfschritt 9.1.3.1b (bitvtest.de): Listen müssen mit den vorgesehenen
HTML-Strukturelementen (``ul``, ``ol``, ``dl``) ausgezeichnet sein; Listen-Markup
darf nicht für Elemente verwendet werden, die keine Listen sind.

Automatisierbar:
- leere Listen (``ul``/``ol``/``dl`` ohne Listeneinträge) — Listen-Markup ohne
  Inhalt (aus dem abdeckenden WCAG-Check ``WCAG_1_3_1_SR_EMPTY_LIST``)
- Listen, deren Einträge sämtlich leer sind — strukturloses/überflüssiges Markup
Nicht automatisierbar: die visuelle Erkennung, ob eine als ``ul``/``ol``
gerenderte Gruppe tatsächlich eine Liste ist bzw. ob sichtbare Listen ohne
entsprechendes Markup ausgekommen sind (manuelle Prüfung mit dem Lists
Bookmarklet, inkl. Navigations-Menüs und Teaser-Kacheln).
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_BITV_TEST_ID = "BITV_9_1_3_1b_HTML_STRUKTURELEMENTE_FUER_LISTEN"


def _eintrag_hat_inhalt(eintrag) -> bool:
    """Ein Listeneintrag zählt als inhaltlich, wenn er Text, Links oder Bilder trägt.

    Nur strukturlose, komplett leere Einträge (ohne Verweis-/Bild-Inhalt und ohne
    ARIA-Beschriftung) sind ein Hinweis auf zweckentfremdetes Listen-Markup.
    """
    if eintrag.get_text(strip=True):
        return True
    if eintrag.find("a", href=True):
        return True
    if eintrag.find("img"):
        return True
    if eintrag.get("aria-label") or eintrag.get("aria-labelledby") or eintrag.get("title"):
        return True
    if eintrag.find(attrs={"aria-label": True}):
        return True
    return False


async def check_html_strukturelemente_fuer_listen(ctx: CheckContext):
    """BITV 9.1.3.1b — Listen-Markup ohne Listeninhalt (Missbrauch von ul/ol/dl)."""
    errors = []
    for lst in ctx.soup.find_all(["ul", "ol", "dl"]):
        if not is_accessible_element(lst):
            continue
        if lst.name == "dl":
            entries = lst.find_all(["dt", "dd"], recursive=False)
        else:
            entries = lst.find_all("li", recursive=False)

        if len(entries) == 0:
            errors.append(finding(
                _BITV_TEST_ID,
                "Leere Liste ohne Listeneinträge — Listen-Markup ohne Inhalt",
                get_dom_path(lst),
            ))
        elif all(not _eintrag_hat_inhalt(e) for e in entries):
            # Alle Einträge sind strukturlos (kein Text, kein Link, kein Bild,
            # keine ARIA-Beschriftung): das Markup bildet keine Liste ab,
            # sondern wird (z. B. als Layout-Raster) zweckentfremdet.
            errors.append(finding(
                _BITV_TEST_ID,
                "Liste nur mit leeren Listeneinträgen — kein Listeninhalt, "
                "Markup wird für Nicht-Listen verwendet",
                get_dom_path(lst),
            ))
    return errors
