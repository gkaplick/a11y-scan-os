"""WCAG 1.4.10 — Reflow: viewport-Meta-Tag vorhanden.

Leeres content="" zählt als vorhanden (der Zoom ist dann nicht explizit
eingeschränkt).
"""
from __future__ import annotations

from ._base import CheckContext, finding


async def check_viewport_missing(ctx: CheckContext):
    """WCAG 1.4.10 — viewport-Meta-Tag fehlt (Seite nicht für Zoom-Reflow optimiert)."""
    page = ctx.page
    try:
        has_viewport = await page.evaluate(
            "() => !!document.querySelector('meta[name=\"viewport\"]')"
        )
    except Exception:
        return []
    if not has_viewport:
        return [finding("WCAG_1_4_10_VIEWPORT_MISSING",
                        "Kein viewport-Meta-Tag gefunden — mobile Reflow gefährdet", "head")]
    return []
