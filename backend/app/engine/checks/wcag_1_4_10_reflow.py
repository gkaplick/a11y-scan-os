"""WCAG 1.4.10 — Reflow: kein horizontaler Überlauf bei 320px.

Fixes (Review): 10-%-Toleranz entfernt (auch +5 % erzeugt Scrollen) und
iframe-Inhalte mitgemessen — über den Viewport hinausragende Frames zählen
zum Überlauf.
"""
from __future__ import annotations

from ._base import CheckContext, finding

_REFLOW_JS = """() => {
    const doc = document.documentElement;
    let scrollWidth = doc.scrollWidth;
    const clientWidth = doc.clientWidth;
    for (const frame of document.querySelectorAll('iframe')) {
        try {
            const rect = frame.getBoundingClientRect();
            if (rect.right > clientWidth) {
                scrollWidth = Math.max(scrollWidth, rect.right);
            }
        } catch (e) { /* cross-origin */ }
    }
    return { scrollWidth, clientWidth };
}"""


async def check_reflow(ctx: CheckContext):
    """WCAG 1.4.10 — horizontaler Überlauf (nur schmale Auflösung ≤ 768px)."""
    if ctx.resolution is None or ctx.resolution > 768:
        return []
    page = ctx.page
    errors = []
    try:
        dims = await page.evaluate(_REFLOW_JS)
        if dims["scrollWidth"] > dims["clientWidth"]:
            width = dims["clientWidth"]
            errors.append(finding("WCAG_1_4_10_REFLOW",
                                  f"Horizontaler Überlauf: Dokument {dims['scrollWidth']}px "
                                  f"breiter als Viewport {width}px",
                                  "html",
                                  resolution=ctx.resolution))
    except Exception:
        pass
    return errors
