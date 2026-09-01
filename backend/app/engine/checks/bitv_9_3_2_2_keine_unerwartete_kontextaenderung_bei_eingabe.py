"""BITV 9.3.2.2 — Keine unerwartete Kontextänderung bei Eingabe.

WCAG 2.1, Technik-Fails F36/F37: Ein Formularfeld (Auswahlliste, Checkbox,
Radio, Textfeld) löst beim Ändern der Eingabe automatisch eine Kontextänderung
aus — etwa ein Auto-Submit des Formulars oder eine Navigation (location.href).

Erkannt wird der kanonische Fehlerfall: ein Formularfeld mit onchange/oninput/
onselect/onkeyup-Handler, dessen Code ein Formular abschickt oder navigiert.
Feld übergreifende dynamische Inhaltsänderungen (AJAX) sind statisch nicht
sicher erkennbar — dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_3_2_2_KEINE_UNERWARTETE_KONTEXTAENDERUNG_BEI_EINGABE"

# Felder, deren Änderung eine Kontextänderung auslösen darf/wird
_CONTROL_EVENTS = ("onchange", "oninput", "onselect", "onkeyup", "onclick")
_CONTROLS = ("select", "input", "textarea", "button", "datalist")

# Auslöser einer Kontextänderung im Handler-Code: Formular abschicken oder
# Navigation (F36/F37). `location =` ist bewusst eng gefasst.
_CONTEXT_CHANGE = re.compile(
    r"""\b(?:form\.)?submit\s*\(|\blocation\.href\s*=|location\.(?:assign|replace)\s*\(|window\.location\s*=""",
    re.IGNORECASE,
)


async def check_keine_unerwartete_kontextaenderung_bei_eingabe(ctx: CheckContext):
    """BITV 9.3.2.2 — Formularfeld mit Auto-Submit/Navigation bei Eingabe."""
    errors = []
    for el in ctx.soup.find_all(_CONTROLS):
        if not is_accessible_element(el):
            continue
        event_code = " ".join(
            filter(None, (el.get(ev) for ev in _CONTROL_EVENTS))
        )
        if not event_code:
            continue
        if not _CONTEXT_CHANGE.search(event_code):
            continue
        errors.append(finding(
            _TEST_ID,
            f"<{el.name}> löst bei Eingabe eine unerwartete Kontextänderung aus "
            "(Auto-Submit/Navigation) — ändert den Kontext ohne Nutzerbestätigung",
            get_dom_path(el),
        ))
    return errors
