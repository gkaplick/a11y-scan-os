"""WCAG 1.4.13 — Zusatzinhalte bei Hover/Fokus (Stub).

Eine korrekte Prüfung müsste Hover- vs. Fokus-Popups per Layout/DOM-Vergleich
erkennen — eigenes Vorhaben; als "nicht implementiert" geführt.
"""
from __future__ import annotations

from ._base import CheckContext, CheckNotImplemented


async def check_hover_focus(ctx: CheckContext):
    """WCAG 1.4.13 — Inhalte nur bei Hover, nicht bei Tastaturfokus (Stub)."""
    raise CheckNotImplemented(
        "WCAG_1_4_13_HOVER_FOCUS: kein Algorithmus — eine CSS-Heuristik über "
        "hasTitle/getComputedStyle trägt nicht (hasTitle==focusTitle immer identisch, "
        "content immer 'normal')"
    )
