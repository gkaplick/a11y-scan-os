"""WCAG 1.3.1 — Info und Beziehungen: Formularfelder programmatisch beschriftet.

Nutzt die geteilte Label-Erkennung (_helpers.element_label). Eine verwaiste
aria-labelledby-Referenz (leeres Ergebnis) gilt nicht als Beschriftung.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import element_label

_SKIP_TYPES = ["submit", "reset", "button", "hidden", "image"]


async def check_form_label(ctx: CheckContext):
    """WCAG 1.3.1 — Formularfeld ohne programmatische Beschriftung."""
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
            "WCAG_1_3_1_FORM_LABEL",
            f"{tag.name.upper()} ohne Label"
            + (f", placeholder='{placeholder}'" if placeholder else ""),
            get_dom_path(tag),
        ))
    return errors
