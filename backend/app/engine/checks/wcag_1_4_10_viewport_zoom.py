"""WCAG 1.4.10 — Reflow: Zoomen durch viewport-Meta nicht blockieren.

Fix (Review): maximum-scale wird geparst (parseFloat) statt per Regex, die
einen Dezimalpunkt verlangte — der Klassiker maximum-scale=1 (Integer) wird
jetzt erkannt. Schwelle = maxScale <= 1.
"""
from __future__ import annotations

from ._base import CheckContext, finding

_VIEWPORT_INSPECT_JS = """() => {
    const meta = document.querySelector('meta[name="viewport"]');
    let content = meta ? meta.getAttribute('content') || '' : '';
    content = content.toLowerCase();
    const maxScaleMatch = content.match(/maximum-scale\\s*=\\s*([\\d.]+)/);
    const maxScale = maxScaleMatch ? parseFloat(maxScaleMatch[1]) : null;
    return {
        hasViewport: !!meta,
        userScalableNo: content.includes('user-scalable=no'),
        maximumScaleLow: maxScale !== null && maxScale <= 1,
        maxScale,
        content,
    };
}"""


async def check_viewport_zoom(ctx: CheckContext):
    """WCAG 1.4.10 — Zoom durch viewport-Meta blockiert (user-scalable=no / maximum-scale<=1)."""
    page = ctx.page
    errors = []
    try:
        data = await page.evaluate(_VIEWPORT_INSPECT_JS)
    except Exception:
        return errors
    if not data["hasViewport"]:
        return errors  # fehlendes Meta behandelt check_viewport_missing
    if data["userScalableNo"] or data["maximumScaleLow"]:
        if data["userScalableNo"]:
            reason = "user-scalable=no"
        elif data["maxScale"] is not None:
            reason = f"maximum-scale={data['maxScale']} (≤ 1)"
        else:
            reason = "maximum-scale ≤ 1"
        errors.append(finding("WCAG_1_4_10_VIEWPORT_ZOOM",
                              f"Zoomen blockiert: {reason} in viewport-Meta",
                              "head > meta[name=viewport]"))
    return errors
