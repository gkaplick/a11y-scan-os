"""WCAG 1.4.12 — Textabstand: Inhalt bleibt bei Spacing-Erhöhung nutzbar.

Fix (Review): neben dem Dokument-Überlauf werden auch per-Element-Abschneidungen
erkannt (overflow:hidden / text-overflow:ellipsis mit scrollHeight>clientHeight).
Meldungen ohne resolution-Feld dedupliziert der Runner über die Auflösungen.
"""
from __future__ import annotations

from ._base import CheckContext, finding

_TEXT_SPACING_JS = """() => {
    const overrides = {
        'letter-spacing': '0.12em',
        'word-spacing': '0.16em',
        'line-height': '1.5',
        'margin-bottom': '2em',
    };
    const styles = document.createElement('style');
    styles.textContent = `
        * { ${Object.entries(overrides).map(([k, v]) => `${k}: ${v} !important;`).join(' ')} }
        p, li, h1, h2, h3, h4, h5, h6, blockquote, dd, dt {
            margin-bottom: 2em !important;
        }
    `;
    document.head.appendChild(styles);
    const doc = document.documentElement;
    const viewport = doc.clientWidth;
    const overflowAfter = doc.scrollWidth > viewport;
    const clipped = [];
    for (const el of document.querySelectorAll(
        'p, li, h1, h2, h3, h4, h5, h6, blockquote, dd, dt, span, a, td, th'
    )) {
        const text = el.textContent.trim();
        if (!text) continue;
        const s = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;
        const clippedH = (s.overflow === 'hidden' || s.overflowX === 'hidden')
            && el.scrollHeight > el.clientHeight + 1;
        const clippedW = (s.overflow === 'hidden' || s.overflowX === 'hidden'
            || s.textOverflow === 'ellipsis')
            && el.scrollWidth > el.clientWidth + 1;
        if (clippedH || clippedW) {
            const path = [];
            let cur = el;
            while (cur && cur !== document.body) {
                let t = cur.tagName.toLowerCase();
                if (cur.id) t += '#' + cur.id;
                else if (cur.className) t += '.' + cur.className.split(' ')[0];
                path.unshift(t);
                cur = cur.parentElement;
            }
            clipped.push({ text: text.slice(0, 40), path: path.join(' > ') });
        }
    }
    styles.remove();
    return { overflowAfter, viewport, clipped };
}"""


async def check_text_spacing(ctx: CheckContext):
    """WCAG 1.4.12 — Überlauf/Abschneidung bei Text-Spacing-Erhöhung."""
    page = ctx.page
    errors = []
    try:
        result = await page.evaluate(_TEXT_SPACING_JS)
        if result["overflowAfter"]:
            errors.append(finding("WCAG_1_4_12_TEXT_SPACING",
                                  f"Inhalt überläuft bei Text-Spacing "
                                  f"(scrollWidth > {result['viewport']}px)",
                                  "html"))
        for item in result["clipped"][:5]:
            errors.append(finding("WCAG_1_4_12_TEXT_SPACING",
                                  f"Text bei Spacing-Erhöhung abgeschnitten: '{item['text']}…'",
                                  item["path"]))
    except Exception:
        pass
    return errors
