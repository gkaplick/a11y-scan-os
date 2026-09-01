"""BITV_9_1_3_2_SINNVOLLE_REIHENFOLGE — Sinnvolle Reihenfolge.

Quelle: docs/bitvtest/9.1.3.2.json (WCAG 1.3.2, Level A).

Automatisiert prüfbares Signal für eine gestörte Lesereihenfolge ist der
Überschriften-Sprung: Springt die Hierarchie eine oder mehrere Ebenen (z. B.
h2 → h4), deutet das darauf hin, dass inhaltlich zusammengehörende Abschnitte
auseinandergerissen wurden oder die Dokumentstruktur nicht der Lesereihenfolge
folgt. Die geteilte Überschriften-Sammlung (_collect_headings) filtert
bereits aria-hidden-Teilbäume.

Ein einzelner Sprung ist kein zwingender Verstoß (Prüfschritt erlaubt das
Auslassen von Ebenen, solange die Reihenfolge logisch bleibt) — der Befund ist
daher als Hinweis auf eine zu prüfende Reihenfolge formuliert. Die vollständige
Bewertung der Screenreader-Lesereihenfolge bleibt manuell.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path
from ._helpers import _collect_headings

_TEST_ID = "BITV_9_1_3_2_SINNVOLLE_REIHENFOLGE"


async def check_sinnvolle_reihenfolge(ctx: CheckContext):
    """BITV_9.1.3.2 — Überschriften-Ebenen springen (Signal für gestörte Reihenfolge)."""
    errors = []
    headings = _collect_headings(ctx)
    prev_level = None
    for u in headings:
        current_level = int(u.name[1])
        if prev_level is not None and current_level > prev_level + 1:
            errors.append(finding(
                _TEST_ID,
                f"Überschriften-Sprung von h{prev_level} zu h{current_level} — "
                "Hinweis auf eine möglicherweise gestörte Lesereihenfolge "
                "(inhaltlich zusammengehörende Abschnitte sind getrennt)",
                get_dom_path(u),
            ))
        prev_level = current_level
    return errors
