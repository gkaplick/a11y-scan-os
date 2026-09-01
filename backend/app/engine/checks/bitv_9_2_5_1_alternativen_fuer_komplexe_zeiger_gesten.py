"""BITV 9.2.5.1 — Alternativen für komplexe Zeiger-Gesten.

WCAG 2.5.1 (A): Funktionen, die über pfadbasierte (Wisch-) oder
Mehrpunkt-Gesten (Pinch, Zwei-Finger) bedient werden, brauchen eine
Alternative über eine einfache Zeigereingabe (G218-Fail vermeiden).

Erkannt werden Multi-Touch-/Gesten-APIs in eingebetteten Skripten und
Inline-Handlern: mehrere gleichzeitige Touches, gesture-Events,
Scale/Rotation, TouchEvent-Konstruktion sowie Gesten-Bibliotheken
(Hammer.js). Reines Scrollverhalten des Browsers (CSS overflow) ist kein
Befund. Ob eine gleichwertige Alternative existiert, ist statisch nicht
verifizierbar — der Befund dokumentiert den Einsatz und verlangt die
Prüfung/Ergänzung einer einfachen Zeigerbedienung. Externe Skripte (src)
sind nicht prüfbar — dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_2_5_1_ALTERNATIVEN_FUER_KOMPLEXE_ZEIGER_GESTEN"

# Mehrpunkt-/Gesten-Signale (hohe Konfidenz)
_GESTURE = re.compile(
    r"touches\s*\.\s*length|changedTouches\s*\.\s*length|gesturestart|gesturechange|gestureend|"
    r"\be\s*\.\s*scale\b|\be\s*\.\s*rotation\b|event\s*\.\s*scale\b|event\s*\.\s*rotation\b|"
    r"new\s+Hammer\b|Hammer\s*\.|hammer\.min\.js|new\s+TouchEvent\b",
    re.IGNORECASE,
)


async def check_alternativen_fuer_komplexe_zeiger_gesten(ctx: CheckContext):
    """BITV 9.2.5.1 — Seite nutzt komplexe Zeiger-Gesten ohne nachweisbare Alternative."""
    fundstellen: list[tuple] = []

    for el in ctx.soup.find_all("script"):
        if el.get("src"):
            continue  # externes Skript — Inhalt nicht prüfbar
        if _GESTURE.search(el.get_text() or ""):
            fundstellen.append((el, "Komplexe Geste in <script>"))

    for el in ctx.soup.find_all(True):
        if not is_accessible_element(el):
            continue
        for attr, code in el.attrs.items():
            if attr.startswith("on") and _GESTURE.search(str(code)):
                fundstellen.append((el, f"Komplexe Geste in {attr}-Handler"))
                break

    errors = []
    for el, quelle in fundstellen[:5]:
        errors.append(finding(
            _TEST_ID,
            f"{quelle} — Funktion reagiert auf eine pfadbasierte/Mehrpunkt-Geste; "
            "zusätzlich einfache Zeigerbedienung (z. B. Einzelklick) bereitstellen",
            get_dom_path(el),
        ))
    return errors
