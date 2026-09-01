"""BITV 9.2.5.2 — Zeigergesten-Eingaben können abgebrochen oder widerrufen werden.

WCAG 2.5.2 (A): Aktionen dürfen nicht bereits beim Down-Event eines Zeigers
ausgeführt werden — sonst gibt es keine Möglichkeit, die Funktion
abzubrechen oder rückgängig zu machen (G210-Fail). Gängige Muster sind
mousedown/pointerdown/touchstart-Handler, die direkt navigieren, Fenster
öffnen, Formulare abschicken oder Elemente anklicken.

Erkannt werden Down-Event-Handler, deren Code eine Kontextänderung/Aktion
auslöst. Die Ausnahme (Down-Auslösen essenziell, z. B. Zeichnen) ist
statisch nicht prüfbar — dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_2_5_2_ZEIGERGESTEN_EINGABEN_KOENNEN_ABGEBROCHEN_ODER_WIDERRUFEN_WERDEN"

# Down-Events: die Aktion feuert bereits beim Drücken, nicht beim Loslassen
_DOWN_EVENTS = ("onmousedown", "onpointerdown", "ontouchstart")

# Aktionen im Handler-Code, die eine sofortige Kontextänderung bewirken
_AKTION = re.compile(
    r"window\.open|\.submit\s*\(|location\s*\.\s*(href|assign|replace)|"
    r"window\.location\s*\.\s*(href|assign|replace)|document\.location|"
    r"\.click\s*\(|history\s*\.\s*(back|go|forward)",
    re.IGNORECASE,
)


async def check_zeigergesten_eingaben_koennen_abgebrochen_oder_widerrufen_werden(ctx: CheckContext):
    """BITV 9.2.5.2 — Down-Event-Trigger führt Aktion ohne Abbruch-Möglichkeit aus."""
    errors = []
    for el in ctx.soup.find_all(True):
        if not is_accessible_element(el):
            continue
        for attr in _DOWN_EVENTS:
            code = el.get(attr)
            if not code:
                continue
            if _AKTION.search(code):
                errors.append(finding(
                    _TEST_ID,
                    f"{attr}-Handler führt die Aktion bereits beim Drücken aus "
                    "(„{code.strip()[:60]}“) — Funktion erst beim Loslassen bzw. "
                    "Abbruch-/Widerruf-Möglichkeit anbieten",
                    get_dom_path(el),
                ))
                break
    return errors[:10]
