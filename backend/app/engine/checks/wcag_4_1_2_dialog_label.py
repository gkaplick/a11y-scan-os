"""WCAG 4.1.2 — Name, Rolle, Wert: role=dialog mit zugänglichem Namen.

Heuristik: nur Anwesenheit von aria-label/aria-labelledby geprüft; eine
verwaiste Referenz wird hier nicht aufgelöst (dokumentierte Einschränkung).
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element


async def check_dialog_label(ctx: CheckContext):
    """WCAG 4.1.2 — role=dialog ohne aria-label/aria-labelledby."""
    errors = []
    for dialog in ctx.soup.find_all(attrs={"role": "dialog"}):
        if is_accessible_element(dialog):
            has_label = dialog.get("aria-label") or dialog.get("aria-labelledby")
            if not has_label:
                errors.append(finding("WCAG_4_1_2_DIALOG_LABEL",
                                      "role='dialog' ohne aria-label/aria-labelledby", get_dom_path(dialog)))
    return errors
