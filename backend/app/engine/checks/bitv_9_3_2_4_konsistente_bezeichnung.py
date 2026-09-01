"""BITV_9_3_2_4_KONSISTENTE_BEZEICHNUNG — Konsistente Bezeichnung.

Quelle: docs/bitvtest/9.3.2.4.json (WCAG 3.2.4, Level AA).

Automatisierte Heuristik: Funktionen, die im Webauftritt wiederholt eingesetzt
werden, sollen überall gleich bezeichnet sein. Der Vergleich ist abhängig vom
DOM-Pfad — derselbe Ziel-Link an derselben Komponenten-Position im
Seiten-Template (z. B. Navigation/Footer) wird über Seiten hinweg verglichen;
derselbe Ziel-Link an unterschiedlichen Positionen (etwa ein externer Link im
Inhalt) ist eine andere Komponente und wird nicht als inkonsistent gemeldet.
Die gemeinsame Logik liegt in ``_konsistente_bezeichnung_befunde``
(_helpers.py) und wird mit dem WCAG-Pendant (wcag_3_2_4_consistent_id.py)
geteilt — beide nutzen denselben Job-Zustand (ctx.state).

Bewusst nur Links verglichen, nicht Buttons/Formulare (deren Zuordnung über
idrefs komplexer ist) — die Befunde sind Hinweise auf inkonsistente
Bezeichnung, keine abschließende Bewertung.
"""
from __future__ import annotations

from ._base import CheckContext
from ._helpers import _konsistente_bezeichnung_befunde

_TEST_ID = "BITV_9_3_2_4_KONSISTENTE_BEZEICHNUNG"


async def check_konsistente_bezeichnung(ctx: CheckContext):
    """BITV_9.3.2.4 — Link-Bezeichnung weicht von früheren Vorkommen derselben
    Komponente (DOM-Pfad) ab."""
    return _konsistente_bezeichnung_befunde(ctx, _TEST_ID)
