"""BITV_9_3_2_3_KONSISTENTE_NAVIGATION — Konsistente Navigation.

Quelle: docs/bitvtest/9.3.2.3.json (WCAG 3.2.3, Level AA).

Automatisierte Heuristik: Navigationsmechanismen, die auf mehreren Seiten
wiederholt vorkommen, sollen in gleicher Reihenfolge und mit gleichen Links
angeordnet sein. Die Navigations-Signatur der ersten geprüften Seite dient als
Referenz; jede Folgeseite mit abweichender Navigation wird als Befund gemeldet
(WCAG 3.2.3, "Consistent Navigation" — axe-Check region/vorgesehen).

Bewusst nur die Reihenfolge/Links der Navigation verglichen, nicht deren
visuelles Layout. Seiten ohne Navigation (kein <nav>, keine menüartige Liste)
sind nicht vergleichbar und werden übersprungen — der Prüfschritt fordert
Konsistenz nur für vorhandene Navigationsmechanismen.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path
from ._helpers import _nav_diff_beschreibung, _nav_signatur, _signaturen_gleich

_TEST_ID = "BITV_9_3_2_3_KONSISTENTE_NAVIGATION"


async def check_konsistente_navigation(ctx: CheckContext):
    """BITV_9.3.2.3 — Navigation weicht von der Startseiten-Navigation ab."""
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
