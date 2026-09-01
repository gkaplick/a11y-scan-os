"""WCAG_3_2_4_CONSISTENT_ID — Konsistente Bezeichnung.

Geteilter Algorithmus mit BITV_9_3_2_4_KONSISTENTE_BEZEICHNUNG
(bitv_9_3_2_4_konsistente_bezeichnung.py): Der Check sammelt pro Job die
Zuordnung (href, DOM-Pfad) → Linktext und meldet jeden Link, dessen
Bezeichnung an derselben Komponenten-Position von der bereits bekannten
Bezeichnung abweicht (WCAG 3.2.4, "Consistent Identification"). Die
Zuordnung teilt sich den Job-Zustand (ctx.state) mit dem BITV-Pendant — beide
erheben dieselbe Signatur aus denselben Seiten. Die gemeinsame Logik liegt in
``_konsistente_bezeichnung_befunde`` (_helpers.py).

Bewusst nur Links verglichen, nicht Buttons/Formulare — die Befunde sind
Hinweise auf inkonsistente Bezeichnung, keine abschließende Bewertung.
"""
from __future__ import annotations

from ._base import CheckContext
from ._helpers import _konsistente_bezeichnung_befunde

_TEST_ID = "WCAG_3_2_4_CONSISTENT_ID"


async def check_consistent_id(ctx: CheckContext):
    """WCAG 3.2.4 — Link-Bezeichnung weicht von früheren Vorkommen derselben
    Komponente (DOM-Pfad) ab."""
    return _konsistente_bezeichnung_befunde(ctx, _TEST_ID)
