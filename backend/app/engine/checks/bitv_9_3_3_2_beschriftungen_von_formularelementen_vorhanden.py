"""BITV_9_3_3_2_BESCHRIFTUNGEN_VON_FORMULARELEMENTEN_VORHANDEN — Beschriftungen von Formularelementen vorhanden.

Prüfschritt 9.3.3.2 (WCAG 3.3.2 Labels or Instructions): Formularelemente
müssen eine sichtbare Beschriftung besitzen. Das ``placeholder``-Attribut
zählt nicht als Beschriftung (es verschwindet bei Eingaben). Beschriftungen
sollen vor (über oder links neben) dem Feld stehen; nur bei Checkboxen und
Radiobuttons steht die Beschriftung üblicherweise rechts daneben.

Automatisiert wird:
- Vorhandensein einer sichtbaren ``<label>``-Beschriftung (``for`` oder
  umschließend) über den geteilten Helfer ``visible_label``,
- die Position der Beschriftung in der linearisierten (Dokument-)Reihenfolge:
  vor dem Feld, außer bei Checkbox/Radiobutton. Grundlage ist die im
  Prüfschritt beschriebene Linearisierung (Miscellaneous > Linearize page).

Nicht automatisiert bleiben die Kennzeichnung von Pflichtfeldern und Hinweise
zum erwarteten Eingabeformat (diese sind nur manuell bewertbar).
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import visible_label

_SKIP_TYPES = ["submit", "reset", "button", "hidden", "image"]


def _document_index(root) -> dict[int, int]:
    """Präorder-Index je Element — Abbild der linearisierten Dokumentreihenfolge."""
    index = {}
    counter = 0
    for el in root.descendants:
        if getattr(el, "name", None):
            index[id(el)] = counter
            counter += 1
    return index


def _label_after_field(field, root, index) -> bool:
    """Sichtbare Beschriftung steht in Dokumentreihenfolge nach dem Feld."""
    eid = field.get("id")
    label = root.find("label", {"for": eid}) if eid else None
    if label is not None and label.get("for") == eid:
        return index.get(id(label), 0) > index.get(id(field), 0)

    # Umschließendes <label>: Liegt kein Text vor dem Feld, folgt die
    # Beschriftung erst nach dem Eingabefeld.
    label = field.find_parent("label")
    if label is None:
        return False
    before = []
    for child in label.children:
        if child is field:
            break
        before.append(child)
    return not any(str(c).strip() for c in before)


async def check_beschriftungen_von_formularelementen_vorhanden(ctx: CheckContext):
    """BITV_9_3_3_2_BESCHRIFTUNGEN_VON_FORMULARELEMENTEN_VORHANDEN — Beschriftungen von Formularelementen vorhanden."""
    errors = []
    root = ctx.soup
    index = _document_index(root)
    for tag in root.find_all(["input", "select", "textarea"]):
        if not is_accessible_element(tag):
            continue
        input_type = tag.get("type", "text").lower()
        if input_type in _SKIP_TYPES:
            continue
        if not visible_label(tag, root):
            errors.append(finding(
                "BITV_9_3_3_2_BESCHRIFTUNGEN_VON_FORMULARELEMENTEN_VORHANDEN",
                f"{tag.name.upper()} ohne sichtbare Beschriftung",
                get_dom_path(tag),
            ))
            continue
        # Checkbox/Radiobutton: Beschriftung steht üblicherweise rechts daneben
        if input_type in ("checkbox", "radio"):
            continue
        if _label_after_field(tag, root, index):
            errors.append(finding(
                "BITV_9_3_3_2_BESCHRIFTUNGEN_VON_FORMULARELEMENTEN_VORHANDEN",
                "Sichtbare Beschriftung steht erst nach dem Formularfeld "
                "(erwartet: vor bzw. über dem Feld)",
                get_dom_path(tag),
            ))
    return errors
