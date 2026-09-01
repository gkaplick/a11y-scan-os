"""BITV_9_2_4_2_SINNVOLLE_DOKUMENTTITEL — Sinnvolle Dokumenttitel.

Der BITV-Prüfschritt 9.2.4.2
wertet zusätzlich nichtssagende Dokumenttitel sowie typografischen Schmuck
(den Screenreader unnötig vorlesen) als \"Nicht voll erfüllt\".
"""
from __future__ import annotations

import re

from ._base import CheckContext, Finding, finding, get_dom_path

_BITV_TEST_ID = "BITV_9_2_4_2_SINNVOLLE_DOKUMENTTITEL"

# Offensichtlich nichtssagende Titel (exakter Treffer nach Trim/Kleinschreibung)
_GENERIC_TITLES = {
    "home", "homepage", "start", "index", "seite", "page", "seite 1", "page 1",
    "untitled", "unbenannt", "dokument", "document", "neu", "new", "new page",
    "eingang",
}

# Typografischer Schmuck (bitvtest 9.2.4.2: etwa ,~~, ====)
_ORNAMENT_RE = re.compile(r"(_{3,}|~{3,}|={3,}|\*{3,}|\.{4,}|…|»|«|—{2,}|-{3,}|>{2,}|<{2,})")


async def check_sinnvolle_dokumenttitel(ctx: CheckContext) -> list[Finding]:
    """BITV 9.2.4.2 — <title> fehlt/leer, nichtssagend oder mit Schmuckzeichen."""
    root = ctx.soup
    title_tag = root.find("title")
    if title_tag is None:
        return [finding(
            _BITV_TEST_ID,
            "Fehlendes <title>-Tag",
            get_dom_path(getattr(root, "head", None) or root),
        )]
    title = title_tag.get_text(" ", strip=True)
    if not title:
        return [finding(_BITV_TEST_ID, "Leeres <title>-Tag", get_dom_path(title_tag))]

    errors = []
    if _ORNAMENT_RE.search(title):
        errors.append(finding(
            _BITV_TEST_ID,
            "Dokumenttitel enthält typografischen Schmuck",
            get_dom_path(title_tag),
        ))
    else:
        lower = title.lower()
        if lower in _GENERIC_TITLES or len(title) <= 2:
            errors.append(finding(
                _BITV_TEST_ID,
                "Dokumenttitel ist nichtssagend (allgemeine oder zu kurze Bezeichnung)",
                get_dom_path(title_tag),
            ))
    return errors
