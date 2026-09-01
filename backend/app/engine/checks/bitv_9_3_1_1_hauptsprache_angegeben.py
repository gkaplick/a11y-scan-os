"""BITV_9_3_1_1_HAUPTSPRACHE_ANGEGEBEN — Hauptsprache angegeben.

Übernommen aus WCAG_3_1_1_LANG; ergänzt um den BITV-Fallback: geprüft wird das
`lang`-Attribut im öffnenden `<html>`-Element, bei XHTML-Seiten ersatzweise
das `xml:lang`-Attribut. Fehlende/leere Angaben und keine BCP-47-artige
Sprachkennung sind Befunde.
"""
from __future__ import annotations

import re

from ._base import CheckContext, Finding, finding, get_dom_path

# BCP-47-Annäherung: 2-3 Buchstaben Primär-Tag, optionale Subtags.
_BCP47_RE = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")


async def check_hauptsprache_angegeben(ctx: CheckContext) -> list[Finding]:
    """BITV_9_3_1_1 — <html> ohne auswertbare Sprachangabe (lang bzw. xml:lang)."""
    root = ctx.soup
    html_tag = root.find("html")
    lang = ""
    if html_tag is not None:
        lang = (html_tag.get("lang") or "").strip()
        if not lang:
            lang = (html_tag.get("xml:lang") or "").strip()
    if html_tag is None or not lang:
        return [finding("BITV_9_3_1_1_HAUPTSPRACHE_ANGEGEBEN",
                        "Fehlende oder leere Sprachangabe im <html>-Element (lang/xml:lang)",
                        get_dom_path(html_tag or root))]
    if not _BCP47_RE.match(lang):
        return [finding("BITV_9_3_1_1_HAUPTSPRACHE_ANGEGEBEN",
                        f"Ungültige Sprachangabe (kein BCP-47-Tag): '{lang}'",
                        get_dom_path(html_tag))]
    return []
