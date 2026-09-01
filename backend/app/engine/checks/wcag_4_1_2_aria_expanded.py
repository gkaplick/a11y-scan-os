"""WCAG 4.1.2 — Name, Rolle, Wert: aria-expanded mit gültigem Wert."""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path


async def check_aria_expanded(ctx: CheckContext):
    """WCAG 4.1.2 — aria-expanded mit ungültigem Wert (nur true/false)."""
    errors = []
    for elem in ctx.soup.find_all(attrs={"aria-expanded": True}):
        value = (elem.get("aria-expanded") or "").lower()
        if value not in ["true", "false"]:
            errors.append(finding("WCAG_4_1_2_ARIA_EXPANDED",
                                  f"Ungültiger aria-expanded-Wert '{value}'", get_dom_path(elem)))
    return errors
