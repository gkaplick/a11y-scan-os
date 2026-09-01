"""WCAG 1.4.4 — Textgröße: Text nach 200%-Zoom nicht abgeschnitten/überlappend.

Fixes (Review): off-canvas-Elemente (komplett außerhalb des Viewports, z. B.
eingefahrene Menüs) gelten nicht als abgeschnitten; Viewport wird auch bei
Exceptions zurückgesetzt (finally); Findings tragen die Auflösung.
Nur Auflösung > 1000px.
"""
from __future__ import annotations

from ._base import CheckContext, finding

_CLIPPED_JS = """() => {
    const innerWidth = window.innerWidth;
    const found = [];
    for (const el of document.querySelectorAll('p, li, h1, h2, h3, h4, h5, h6, td, th, span')) {
        if (el.closest('[hidden], [aria-hidden="true"]')) continue;
        const rect = el.getBoundingClientRect();
        if (rect.left >= innerWidth || rect.right <= 0) continue;  // off-canvas
        if (rect.right > innerWidth + 2 && el.textContent.trim().length > 0) {
            const path = [];
            let cur = el;
            while (cur && cur !== document.body) {
                let t = cur.tagName.toLowerCase();
                if (cur.id) t += '#' + cur.id;
                else if (cur.className) t += '.' + cur.className.split(' ')[0];
                path.unshift(t);
                cur = cur.parentElement;
            }
            found.push({ text: el.textContent.trim().slice(0, 40), path: path.join(' > ') });
        }
    }
    return found;
}"""


async def check_resize_text(ctx: CheckContext):
    """WCAG 1.4.4 — Text nach 200%-Zoom abgeschnitten/überlappend."""
    if ctx.resolution is None or ctx.resolution <= 1000:
        return []
    page = ctx.page
    errors = []
    viewport = page.viewport_size or {}
    half_width = max(320, viewport["width"] // 2)
    overflow = {"scrollWidth": 0, "clientWidth": 0}
    clipped = []
    try:
        await page.set_viewport_size({"width": half_width, "height": viewport["height"]})
        await page.wait_for_timeout(300)
        overflow = await page.evaluate(
            """() => {
                const doc = document.documentElement;
                return { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth };
            }"""
        )
        clipped = await page.evaluate(_CLIPPED_JS)
    except Exception:
        pass
    finally:
        try:
            await page.set_viewport_size(viewport)
        except Exception:
            pass

    if overflow["scrollWidth"] > overflow["clientWidth"] + 20:
        errors.append(finding(
            "WCAG_1_4_4_RESIZE",
            f"Horizontaler Überlauf bei 200%-Zoom "
            f"({overflow['scrollWidth']}px vs. {overflow['clientWidth']}px)",
            "html", ctx.resolution,
        ))
    for item in clipped[:5]:
        errors.append(finding(
            "WCAG_1_4_4_RESIZE",
            f"Text bei 200%-Zoom abgeschnitten: '{item['text']}…'",
            item["path"], ctx.resolution,
        ))
    return errors
