"""WCAG 2.5.4 — Bewegungsaktivierung (Alternativen zu Gerätebewegung).

Gleiche Regel wie BITV 9.2.5.4 (A): Funktionen, die über Gerätebewegung
ausgelöst werden (Beschleunigungs-/Orientierungssensoren), brauchen
alternative Eingabemöglichkeiten und müssen abschaltbar sein (z. B. beim
„Shake"-Geste oder Neigen des Geräts).

Erkannt werden die Bewegungs-APIs in eingebetteten Skripten und
Inline-Handlern: devicemotion, deviceorientation, DeviceMotionEvent,
DeviceOrientationEvent. Dass eine gleichwertige Alternative existiert, ist
statisch nicht verifizierbar — der Befund dokumentiert den Einsatz der
Bewegungs-API und verlangt die Prüfung/Ergänzung einer alternativen Bedienung.
Externe Skripte (src) lassen sich im Quelltext nicht prüfen — dokumentierte
Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "WCAG_2_5_4_MOTION"

_MOTION = re.compile(
    r"devicemotion|deviceorientation(?:absolute)?|DeviceMotionEvent|DeviceOrientationEvent",
    re.IGNORECASE,
)


async def check_motion(ctx: CheckContext):
    """WCAG 2.5.4 — Seite nutzt Gerätebewegung ohne nachweisbare Alternative."""
    fundstellen: list[tuple] = []

    for el in ctx.soup.find_all("script"):
        if el.get("src"):
            continue  # externes Skript — Inhalt nicht prüfbar
        code = el.get_text() or ""
        if _MOTION.search(code):
            fundstellen.append((el, "Bewegungs-API in <script>"))

    for el in ctx.soup.find_all(True):
        if not is_accessible_element(el):
            continue
        for attr, code in el.attrs.items():
            if attr.startswith("on") and _MOTION.search(str(code)):
                fundstellen.append((el, f"Bewegungs-API in {attr}-Handler"))
                break

    errors = []
    for el, quelle in fundstellen[:5]:
        errors.append(finding(
            _TEST_ID,
            f"{quelle} — Funktion reagiert auf Gerätebewegung; alternative "
            "Eingabemöglichkeit bereitstellen und Bewegungseingabe abschaltbar machen",
            get_dom_path(el),
        ))
    return errors
