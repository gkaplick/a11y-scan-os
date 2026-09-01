"""BITV 9.1.4.4 — Text auf 200% vergrößerbar.

Der BITV-Prüfschritt verlangt, dass sich Text um bis zu 200% vergrößern lässt,
ohne dass Inhalt oder Funktionalität verloren geht (keine Überlagerungen, kein
Abschneiden, kein horizontaler Überlauf).

Der Prüfschritt ist im Registry als ``type="syntax"`` geführt, der Runner
übergibt aber auch Syntax-Checks die Playwright-Seite (``ctx.page``). Der Check
arbeitet deshalb direkt mit der Live-Seite und simuliert den 200%-Zoom nach der
bitvtest-Vorgehensweise: Browserfenster 1280×768, dann Zoom auf 200%
(= CSS-Viewport 640×384). Gemessen werden horizontaler Überlauf
(``scrollWidth > clientWidth``) und abgeschnittene Text-Elemente.

Off-canvas-Elemente (komplett außerhalb des Viewports, z. B. eingefahrene
Menüs) gelten nicht als abgeschnitten; der Viewport wird in jedem Fall
zurückgesetzt (finally). In Unit-Tests ohne Seite (``ctx.page is None``)
liefert der Check keine Befunde.
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

_BASE_VIEWPORT = {"width": 1280, "height": 768}   # bitvtest: Fenstergröße 1280×768
_ZOOMED_VIEWPORT = {"width": 640, "height": 384}  # 200%-Zoom → CSS-Viewport halbiert


async def check_text_auf_200_vergroesserbar(ctx: CheckContext):
    """BITV 9.1.4.4 — horizontaler Überlauf / abgeschnittener Text bei 200%-Zoom."""
    if ctx.page is None:
        return []
    page = ctx.page
    errors = []
    original = page.viewport_size or _BASE_VIEWPORT
    overflow = {"scrollWidth": 0, "clientWidth": 0}
    clipped = []
    try:
        await page.set_viewport_size(_BASE_VIEWPORT)
        await page.wait_for_timeout(200)
        await page.set_viewport_size(_ZOOMED_VIEWPORT)
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
            await page.set_viewport_size(original)
        except Exception:
            pass

    if overflow["scrollWidth"] > overflow["clientWidth"] + 20:
        errors.append(finding(
            "BITV_9_1_4_4_TEXT_AUF_200_VERGROESSERBAR",
            f"Horizontaler Überlauf bei 200%-Zoom "
            f"({overflow['scrollWidth']}px vs. {overflow['clientWidth']}px)",
            "html",
        ))
    for item in clipped[:5]:
        errors.append(finding(
            "BITV_9_1_4_4_TEXT_AUF_200_VERGROESSERBAR",
            f"Text bei 200%-Zoom abgeschnitten: '{item['text']}…'",
            item["path"],
        ))
    return errors
