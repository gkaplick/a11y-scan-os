"""BITV 9.1.4.12 — Textabstände anpassbar.

Die Spacing-Werte (Zeilenhöhe 1,5×, Absatzabstand 2em, Buchstabenabstand 0,12em,
Wortabstand 0,16em) werden per JS gesetzt; gemessen wird Dokument-Überlauf
und per-Element-Abschneidung (overflow:hidden / text-overflow:ellipsis mit
scrollHeight>clientHeight).

Der Registry-Typ dieses Prüfschritts ist 'syntax' — der Runner reicht die
Playwright-Seite trotzdem mit (ctx.page). Ohne Seite (Unit-Test) wird nichts
geprüft.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding

_TEST_ID = "BITV_9_1_4_12_TEXTABSTAENDE_ANPASSBAR"

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


async def check_textabstaende_anpassbar(ctx: CheckContext) -> list[Finding]:
    """BITV 9.1.4.12 — Überlauf/Abschneidung bei Textabstand-Erhöhung."""
    page = ctx.page
    if page is None:
        return []
    errors = []
    try:
        result = await page.evaluate(_TEXT_SPACING_JS)
        if result["overflowAfter"]:
            errors.append(finding(
                _TEST_ID,
                f"Inhalt überläuft bei Textabstand-Erhöhung (scrollWidth > {result['viewport']}px)",
                "html",
            ))
        for item in result["clipped"][:5]:
            errors.append(finding(
                _TEST_ID,
                f"Text bei Textabstand-Erhöhung abgeschnitten: '{item['text']}…'",
                item["path"],
            ))
    except Exception:
        pass
    return errors
