"""WCAG_2_4_6_FIRST_HEADING — Erste Überschrift kein h1.

WCAG 2.4.6 "Überschriften und Labels" (Level AA): Überschriften und Labels
beschreiben Thema oder Zweck. Der Haupttitel einer Seite wird üblicherweise
als h1 ausgezeichnet; beginnt die Überschriften-Hierarchie mit einer tieferen
Ebene, ist der Haupttitel nicht als solcher erkennbar.

Automatisiert geprüft: Die erste Überschrift in Dokument-Reihenfolge (geteilte
Sammlung _collect_headings, aria-hidden bereits gefiltert) ist kein h1. Seiten
ohne Überschriften lösen keinen Befund aus (keine Hierarchie zu bewerten —
Strukturprobleme gehören zu 1.3.1/9.1.3.1a).
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path
from ._helpers import _collect_headings

_TEST_ID = "WCAG_2_4_6_FIRST_HEADING"


async def check_first_heading(ctx: CheckContext):
    """WCAG 2.4.6 — Die erste Überschrift der Seite ist kein h1."""
    headings = _collect_headings(ctx)
    if not headings:
        return []
    erste = headings[0]
    if erste.name == "h1":
        return []
    return [finding(
        _TEST_ID,
        f"Die erste Überschrift der Seite ist kein h1, sondern {erste.name} — "
        "der Haupttitel ist nicht als h1 ausgezeichnet",
        get_dom_path(erste),
    )]
