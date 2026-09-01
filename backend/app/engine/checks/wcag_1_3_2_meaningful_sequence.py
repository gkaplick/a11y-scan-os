"""WCAG_1_3_2_MEANINGFUL_SEQUENCE — Bedeutung durch Reihenfolge.

Geteilter Algorithmus mit BITV_9_1_3_2_SINNVOLLE_REIHENFOLGE
(bitv_9_1_3_2_sinnvolle_reihenfolge.py): Der Überschriften-Sprung ist das
automatisierbare Signal für eine gestörte Lesereihenfolge. Die geteilte
Überschriften-Sammlung (_collect_headings) filtert bereits aria-hidden-Teilbäume.

Ein einzelner Sprung ist kein zwingender Verstoß (die Reihenfolge kann
trotzdem logisch sein) — der Befund ist als Hinweis formuliert. Die
vollständige Bewertung der Screenreader-Lesereihenfolge bleibt manuell.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path
from ._helpers import _collect_headings

_TEST_ID = "WCAG_1_3_2_MEANINGFUL_SEQUENCE"


async def check_meaningful_sequence(ctx: CheckContext):
    """WCAG 1.3.2 — Überschriften-Ebenen springen (Signal für gestörte Reihenfolge)."""
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
