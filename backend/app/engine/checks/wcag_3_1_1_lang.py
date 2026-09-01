"""WCAG 3.1.1 — Sprache der Seite: <html lang> auswertbar.

Fix (Review): BCP-47-artige Validierung der Sprachangabe — lang="englisch"
ist keine gültige Sprache (fehlende, leere und unauswertbare Angaben sind
Befunde).
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path

# BCP-47-Annäherung: 2-3 Buchstaben Primär-Tag, optionale Subtags.
_BCP47_RE = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")


async def check_html_lang(ctx: CheckContext):
    """WCAG 3.1.1 — <html lang> fehlt, leer oder kein BCP-47-Tag."""
    root = ctx.soup
    html_tag = root.find("html")
    lang = (html_tag.get("lang") or "").strip() if html_tag else ""
    if not html_tag or not lang:
        errors = [finding("WCAG_3_1_1_LANG", "Fehlendes oder leeres 'lang'-Attribut",
                          get_dom_path(html_tag or root))]
        return errors
    if not _BCP47_RE.match(lang):
        errors = [finding("WCAG_3_1_1_LANG",
                          f"Ungültiges lang-Attribut (kein BCP-47-Tag): '{lang}'",
                          get_dom_path(html_tag))]
        return errors
    return []
