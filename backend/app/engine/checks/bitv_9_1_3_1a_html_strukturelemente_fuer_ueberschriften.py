"""BITV_9_1_3_1a_HTML_STRUKTURELEMENTE_FUER_UEBERSCHRIFTEN — HTML-Strukturelemente für Überschriften.

Quelle: docs/bitvtest/9.1.3.1a.json (WCAG 1.3.1, Level A).

Automatisiert prüfbar ist der ARIA-Teil der Anforderung: Visuelle
Überschriften, die nicht mit h1-h6, sondern mit role="heading" ausgezeichnet
sind, benötigen ein passendes aria-level-Attribut (ARIA12). Ein
role="heading" ohne aria-level bzw. mit ungültigem aria-level ist nicht
korrekt ausgezeichnet.

Bewusst NICHT übernommen wird der WCAG-Check WCAG_1_3_1_HEADING_SKIP
(Überschriften-Sprung, z. B. h2 → h4): Der Prüfschritt erlaubt das Auslassen
von Hierarchie-Ebenen ausdrücklich, solange die Abfolge der Überschriften
logisch bleibt. Die positive Anforderung "sichtbare Überschriften sind als
solche ausgezeichnet" sowie die inhaltliche Logik der Hierarchie sind manuell
zu bewerten.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_1_3_1a_HTML_STRUKTURELEMENTE_FUER_UEBERSCHRIFTEN"

_ARIA_LEVEL_RE = re.compile(r"^[1-9]\d*$")


async def check_html_strukturelemente_fuer_ueberschriften(ctx: CheckContext):
    """BITV_9_1_3_1a — role=heading ohne gültiges aria-level."""
    errors = []
    for el in ctx.soup.find_all(attrs={"role": "heading"}):
        if not is_accessible_element(el):
            continue
        aria_level = el.get("aria-level")
        if aria_level is None or not _ARIA_LEVEL_RE.match(aria_level.strip()):
            level_info = f"aria-level='{aria_level}'" if aria_level is not None else "ohne aria-level"
            errors.append(finding(
                _TEST_ID,
                f"role='heading' {level_info} — aria-level muss eine gültige "
                "Überschriften-Ebene (positive ganze Zahl) angeben (ARIA12)",
                get_dom_path(el),
            ))
    return errors
