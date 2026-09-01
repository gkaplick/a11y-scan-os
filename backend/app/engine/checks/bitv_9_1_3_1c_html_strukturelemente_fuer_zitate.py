"""BITV 9.1.3.1c — HTML-Strukturelemente für Zitate.

WCAG 1.3.1 (Info und Beziehungen): eigenständige Zitat-Abschnitte sollen mit
dem dafür vorgesehenen HTML-Strukturelement ausgezeichnet sein (blockquote/q).
Gefunden wird:
- Elemente, die ein Zitat nur visuell markieren (Klasse zitat/quote/citation/
  blockquote) oder per cite-Attribut kennzeichnen, ohne blockquote/q-Semantik,
- Textabsätze, die ausschließlich typografisch („…") als Zitat markiert sind.

Als ausreichend ausgezeichnet gelten blockquote/q sowie role="blockquote"
(ARIA übermittelt die Zitat-Semantik). Inline-Zitate und Zitate ohne jede
Zitat-Markierung sind nicht prüfbar — dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_1_3_1c_HTML_STRUKTURELEMENTE_FUER_ZITATE"

_QUOTE_CLASS = re.compile(r"(zitat|quote|citation|blockquote)", re.IGNORECASE)
_QUOTE_CHARS = set("„“”„“”‟\"'")
# Blöcke, in denen ein eigenständiger Zitat-Abschnitt stehen kann
_BLOCK_CONTAINERS = ("p", "div", "li", "td", "section", "article", "figure")


def _ist_zitat_inhalt(el) -> bool:
    """Quote-artiger Inhalt: Anführungszeichen oder ein längerer Standalone-Block."""
    text = el.get_text() or ""
    if any(c in text for c in _QUOTE_CHARS):
        return True
    return len(" ".join(text.split())) >= 120


def _ist_typografischer_zitatblock(text: str) -> bool:
    """Der gesamte Block ist typografisch als Zitat markiert („…" bzw. "…")."""
    t = " ".join(text.split())
    if len(t) < 15:
        return False
    return (t.startswith("„") and t.endswith('"')) or \
           (t.startswith("“") and t.endswith("”")) or \
           (t.startswith('"') and t.endswith('"'))


async def check_html_strukturelemente_fuer_zitate(ctx: CheckContext):
    """BITV 9.1.3.1c — Zitat nur visuell/typografisch statt blockquote/q."""
    errors = []
    for el in ctx.soup.find_all(_BLOCK_CONTAINERS):
        if not is_accessible_element(el):
            continue
        if el.find_parent(["blockquote", "q"]):
            continue  # bereits innerhalb einer Zitat-Auszeichnung
        if el.get("role") == "blockquote":
            continue  # ARIA-Semantik vorhanden

        if el.get("cite") is not None:
            grund = "cite-Attribut kennzeichnet ein Zitat ohne blockquote-Semantik"
        else:
            klassen = " ".join(el.get("class") or [])
            if _QUOTE_CLASS.search(klassen) and _ist_zitat_inhalt(el):
                grund = (f"Klasse {klassen!r} markiert das Zitat nur visuell "
                         "— blockquote statt visueller Markierung nutzen")
            elif _ist_typografischer_zitatblock(el.get_text() or ""):
                grund = ("Text ist nur typografisch (Anführungszeichen) als Zitat "
                         "markiert — blockquote/q nutzen")
            else:
                continue

        errors.append(finding(_TEST_ID, grund, get_dom_path(el)))
    return errors[:10]
