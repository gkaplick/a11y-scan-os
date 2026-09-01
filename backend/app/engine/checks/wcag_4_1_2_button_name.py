"""WCAG 4.1.2 — Name, Rolle, Wert: Button mit zugänglichem Namen.

Fix (Review): der zugängliche Name wird per AccName-Heuristik aufgelöst
(aria-labelledby → aria-label → Text → title → Kind-<img alt>) statt nur
Text+aria-label. Ein leeres aria-labelledby (verwaist) gilt nicht als Name.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import has_accessible_name


async def check_button_name(ctx: CheckContext):
    """WCAG 4.1.2 — Button ohne zugänglichen Namen (AccName + Label)."""
    errors = []
    root = ctx.soup
    for button in ctx.soup.find_all("button"):
        if is_accessible_element(button) and not has_accessible_name(button, root):
            errors.append(finding("WCAG_4_1_2_BUTTON_NAME",
                                  "<button> ohne zugänglichen Namen", get_dom_path(button)))
    return errors
