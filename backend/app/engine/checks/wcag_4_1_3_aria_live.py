"""WCAG 4.1.3 — Statusmeldungen: aria-live mit gültigem Wert."""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path


async def check_aria_live(ctx: CheckContext):
    """WCAG 4.1.3 — aria-live mit ungültigem Wert (off/polite/assertive)."""
    errors = []
    for elem in ctx.soup.find_all(attrs={"aria-live": True}):
        value = (elem.get("aria-live") or "").lower()
        if value not in ["off", "polite", "assertive"]:
            errors.append(finding("WCAG_4_1_3_ARIA_LIVE",
                                  f"Ungültiger aria-live-Wert '{value}'", get_dom_path(elem)))
    return errors
