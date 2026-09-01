"""WCAG 4.1.2 — Name, Rolle, Wert: aria-hidden mit gültigem Wert.

Fix (Review): aria-hidden="" ist kein gültiger ARIA-Wert — nur true/false
sind erlaubt. Leere Werte sind ein Befund.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element


async def check_aria_hidden(ctx: CheckContext):
    """WCAG 4.1.2 — aria-hidden-Wert außerhalb true/false."""
    errors = []
    for elem in ctx.soup.find_all(attrs={"aria-hidden": True}):
        if is_accessible_element(elem):
            value = (elem.get("aria-hidden") or "").lower()
            if value not in ["true", "false"]:
                errors.append(finding("WCAG_4_1_2_ARIA_HIDDEN",
                                      f"Ungültiger Wert für aria-hidden '{value}'", get_dom_path(elem)))
    return errors
