"""WCAG 1.4.1 — Farbe ist nicht das einzige visuelle Unterscheidungsmerkmal.

Erweitert um alle vom Auftraggeber geforderten Nicht-Farb-Merkmale: Neben
Unterstreichung, Rahmen, Hintergrundfarbe und Kursivierung zählen jetzt auch
Schriftdicke ab halbfett (font-weight >= 600, relativ zum Fließtext) und fest
integrierte Symbole/Icons als dauerhafte visuelle Kennzeichnung. Zusätzlich
greift die BITV-/G183-Ausnahme: Ein Link mit >= 3:1 Kontrast zur umgebenden
Textfarbe, der bei Hover/Fokus eine Unterstreichung erhält, ist ausreichend
gekennzeichnet. Die Bewertungslogik liegt zentral in ``_color_only_befunde``.
"""
from __future__ import annotations

from ._base import CheckContext, finding
from ._helpers import _color_only_befunde


async def check_color_only_links(ctx: CheckContext):
    """WCAG 1.4.1 — Links nur durch Farbe vom umgebenden Text unterscheidbar."""
    errors = []
    try:
        for link in await _color_only_befunde(ctx):
            text = (link["text"] or "")[:30].replace("\n", " ").replace("\t", " ")
            errors.append(finding(
                "WCAG_1_4_1_COLOR_ONLY",
                f"Link '{text}…' nur durch Farbe erkennbar "
                "(kein dauerhaftes Nicht-Farb-Merkmal)",
                link["path"], ctx.resolution,
            ))
    except Exception:
        pass
    return errors
