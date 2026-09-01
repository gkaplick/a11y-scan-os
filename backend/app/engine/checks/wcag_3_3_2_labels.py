"""WCAG 3.3.2 — Labels oder Anweisungen: sichtbare Beschriftung.

Nutzt _helpers.visible_label: Nur sichtbarer <label>-Text zählt — aria-label,
title und placeholder sind keine sichtbaren Beschriftungen.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import visible_label

_SKIP_TYPES = ["submit", "reset", "button", "hidden", "image"]


async def check_form_label(ctx: CheckContext):
    """WCAG 3.3.2 — Formularfeld ohne sichtbares Label."""
    errors = []
    root = ctx.soup
    for tag in root.find_all(["input", "select", "textarea"]):
        if not is_accessible_element(tag):
            continue
        input_type = tag.get("type", "text").lower()
        if input_type in _SKIP_TYPES:
            continue
        if visible_label(tag, root):
            continue
        errors.append(finding(
            "WCAG_3_3_2_LABELS",
            f"{tag.name.upper()} ohne sichtbares Label", get_dom_path(tag),
        ))
    return errors
