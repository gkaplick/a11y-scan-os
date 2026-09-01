"""BITV 9.1.3.1h — Beschriftung von Formularelementen programmatisch ermittelbar.

Die geteilte
Label-Erkennung (_helpers.element_label) prüft, ob ein Formularfeld einen
programmatisch ermittelbaren Namen hat (aria-label, aria-labelledby, label[for],
umschließendes <label>, title). Eine verwaiste aria-labelledby-Referenz
(leeres Ergebnis) gilt nicht als Beschriftung.

Gruppenbeschriftungen (fieldset/legend, role="group"), die optgroup-Gliederung
hierarchischer Auswahllisten und zusätzliche Beschriftungen über
aria-describedby erfordern eine manuelle Bewertung, ob die Gruppen- bzw.
Zusatzbeschriftung für das Verständnis nötig ist — sie bleiben hier
unberücksichtigt.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding, get_dom_path, is_accessible_element
from ._helpers import element_label

_SKIP_TYPES = ["submit", "reset", "button", "hidden", "image"]
_TEST_ID = "BITV_9_1_3_1h_BESCHRIFTUNG_VON_FORMULARELEMENTEN_PROGRAMMATISCH_ERMITTELBAR"


async def check_beschriftung_von_formularelementen_programmatisch_ermittelbar(ctx: CheckContext) -> list[Finding]:
    """BITV 9.1.3.1h — Formularfeld ohne programmatisch ermittelbare Beschriftung."""
    errors = []
    root = ctx.soup
    for tag in root.find_all(["input", "select", "textarea"]):
        if not is_accessible_element(tag):
            continue
        input_type = tag.get("type", "text").lower()
        if input_type in _SKIP_TYPES:
            continue
        if element_label(tag, root):
            continue
        placeholder = tag.get("placeholder", "")
        errors.append(finding(
            _TEST_ID,
            f"{tag.name.upper()} ohne programmatisch ermittelbare Beschriftung"
            + (f", placeholder='{placeholder}'" if placeholder else ""),
            get_dom_path(tag),
        ))
    return errors
