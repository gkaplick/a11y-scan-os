"""BITV_9_1_4_1_OHNE_FARBEN_NUTZBAR — Ohne Farben nutzbar.

Die Bewertungslogik liegt zentral in ``_color_only_befunde``
(``_helpers.py``): Ein Fließtext-Link ist ausreichend gekennzeichnet, wenn er
ein dauerhaftes Nicht-Farb-Merkmal trägt (Unterstreichung, Rahmen,
Hintergrund, Kursivierung, Fettung ab halbfett, festes Symbol/Icon). Die
bitvtest-Ausnahme greift nur, wenn der Link >= 3:1 Kontrast zur umgebenden
Textfarbe hat UND bei Hover/Fokus zusätzlich hervorgehoben wird (Unterstreichung)
— ein reiner 3:1-Kontrast ohne Hover/Fokus-Unterstreichung genügt laut
bitvtest-Formulierung („…müssen dann aber bei Fokuserhalt zusätzlich
hervorgehoben werden") nicht.

Benötigt Computed Styles (Playwright) — der Runner übergibt die Seite auch an
Syntax-Checks. Ohne Seite (Unit-Test) liefert der Check keine Befunde.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding
from ._helpers import _color_only_befunde

_BITV_TEST_ID = "BITV_9_1_4_1_OHNE_FARBEN_NUTZBAR"


async def check_ohne_farben_nutzbar(ctx: CheckContext) -> list[Finding]:
    """BITV 9.1.4.1 — Links nur durch Farbe vom umgebenden Text unterscheidbar."""
    if ctx.page is None:
        return []  # Computed Styles sind ohne Playwright nicht prüfbar
    errors = []
    try:
        for link in await _color_only_befunde(ctx):
            text = (link["text"] or "")[:30].replace("\n", " ").replace("\t", " ")
            errors.append(finding(
                _BITV_TEST_ID,
                f"Link '{text}…' nur durch Farbe vom Text unterscheidbar "
                "(kein dauerhaftes Nicht-Farb-Merkmal, keine "
                "Hover/Fokus-Unterstreichung)",
                link["path"],
            ))
    except Exception:
        pass
    return errors
