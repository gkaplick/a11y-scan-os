"""WCAG 1.4.1 — Farbblind-Simulation (Stub).

Das Kriterium brauchte eine Farbfehlsichtigkeits-Matrix auf die effektiven
Farben; eine reine CSS-Filter-"Simulation" wäre ein No-op (getComputedStyle
ignoriert ``el.style.filter``). Bis dahin als "nicht implementiert" geführt
statt fälschlich zu bestehen.
"""
from __future__ import annotations

from ._base import CheckContext, CheckNotImplemented


async def check_colorblind_simulation(ctx: CheckContext):
    """WCAG 1.4.1 — Kontrast unter Farbblindheits-Simulationen (Stub)."""
    raise CheckNotImplemented(
        "WCAG_1_4_1_COLORBLIND_SIMULATION: keine Farbblind-Simulation implementiert "
        "(CSS-Filter war ein No-op; korrekt wäre eine Farbmatrix auf den Effektiv-Farben)"
    )
