"""WCAG 1.3.4 — Orientierung (keine Beschränkung der Bildschirmausrichtung).

Gleiche Regel wie BITV 9.1.3.4: Inhalte sollen sich an die nutzergewählte
Ausrichtung des Ausgabegeräts anpassen (Hoch-/Querformat). Eine
programmatische Sperre der Orientierung (screen.orientation.lock() bzw.
proprietäre Varianten) erzwingt eine einzelne Ausrichtung und ist ein
G217-Fail.

Erkannt wird der Aufruf der Lock-APIs in eingebetteten Skripten und
Inline-Handlern. Responsives CSS (z. B. @media (orientation: portrait)) ist
KEIN Befund. Externe Skripte (src) sind statisch nicht prüfbar —
dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "WCAG_1_3_4_ORIENTATION"

_ORIENT_LOCK = re.compile(
    r"orientation\s*\.\s*lock\s*\(|lockOrientation\s*\(|msLockOrientation\s*\(|"
    r"mozLockOrientation\s*\(|webkitLockOrientation\s*\(",
    re.IGNORECASE,
)


async def check_orientation(ctx: CheckContext):
    """WCAG 1.3.4 — Seite sperrt die Bildschirmausrichtung (Orientierungs-Lock)."""
    fundstellen: list[tuple] = []

    for el in ctx.soup.find_all("script"):
        if el.get("src"):
            continue  # externes Skript — Inhalt nicht prüfbar
        if _ORIENT_LOCK.search(el.get_text() or ""):
            fundstellen.append((el, "Orientierungs-Lock in <script>"))

    for el in ctx.soup.find_all(True):
        if not is_accessible_element(el):
            continue
        for attr, code in el.attrs.items():
            if attr.startswith("on") and _ORIENT_LOCK.search(str(code)):
                fundstellen.append((el, f"Orientierungs-Lock in {attr}-Handler"))
                break

    errors = []
    for el, quelle in fundstellen[:5]:
        errors.append(finding(
            _TEST_ID,
            f"{quelle} — die Bildschirmausrichtung wird programmatisch gesperrt; "
            "Inhalt in Hoch- UND Querformat anbieten (Sperre entfernen)",
            get_dom_path(el),
        ))
    return errors
