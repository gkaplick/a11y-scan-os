"""WCAG_3_2_3_CONSISTENT_NAV — Konsistente Navigation.

Geteilter Algorithmus mit BITV_9_3_2_3_KONSISTENTE_NAVIGATION
(bitv_9_3_2_3_konsistente_navigation.py) — beide nutzen dieselben
seitenübergreifenden Signaturen im Job-Zustand (ctx.state) und vergleichen ab
der zweiten Seite gegen die Navigation der Startseite.

Der Check meldet nur Abweichungen, wenn eine Seite überhaupt eine Navigation
hat — Seiten ohne Navigation sind nicht vergleichbar (WCAG 3.2.3 verlangt
Konsistenz nur für vorhandene Navigationsmechanismen).
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path
from ._helpers import _nav_diff_beschreibung, _nav_signatur, _signaturen_gleich

_TEST_ID = "WCAG_3_2_3_CONSISTENT_NAV"


async def check_consistent_nav(ctx: CheckContext):
    """WCAG 3.2.3 — Navigation weicht von der Startseiten-Navigation ab."""
    state = ctx.state if ctx.state is not None else {}
    navs, sig = _nav_signatur(ctx)
    if not sig:
        # Keine Navigation auf dieser Seite → nicht vergleichbar, kein Befund
        return []

    referenz = state.get("nav_sig")
    if referenz is None:
        # Erste Seite mit Navigation: als Referenz merken
        state["nav_sig"] = sig
        state["nav_first_url"] = ctx.url
        return []

    if _signaturen_gleich(referenz, sig):
        return []

    path = get_dom_path(navs[0]) if navs else ""
    return [finding(
        _TEST_ID,
        "Navigation unterscheidet sich von der Startseite — "
        "Navigationsmechanismen sollen innerhalb des Webauftritts "
        "einheitlich sein (konsistente Navigation)",
        path,
        detail=f"Abweichung: {_nav_diff_beschreibung(referenz, sig)} (Referenz: {state.get('nav_first_url', 'erste Seite')})",
    )]
