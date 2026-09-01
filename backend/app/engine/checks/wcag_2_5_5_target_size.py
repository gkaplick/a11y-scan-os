"""WCAG 2.5.5 — Zielgröße: Touch-Ziele mindestens 44×44 CSS-px (AAA).

Fixes (Review): 2.5.5-Ausnahmen respektiert, sonst Massen-FP:
- Inline-Links in Sätzen (in Textfluss eingebettet),
- Spacing-Ausnahme (mind. 24px freier Raum rund um das Ziel),
- native User-Agent-Kontrollen (checkbox/radio).
Nur Auflösung ≤ 768px.
"""
from __future__ import annotations

from ._base import CheckContext, finding

_TARGET_SIZE_JS = """() => {
    const selector = 'a, button, input, select, textarea, [role="button"], [role="link"]';
    const targets = Array.from(document.querySelectorAll(selector)).filter(el => {
        const s = getComputedStyle(el);
        if (s.display === 'none' || s.visibility === 'hidden') return false;
        // Native UA-Kontrollen sind laut 2.5.5 ausgenommen.
        if (el.matches('input[type="checkbox"], input[type="radio"]')) return false;
        // Inline-Ausnahme: in Text eingebettete Links (Satzfluss).
        const parent = el.parentElement;
        const inText = parent && /^(p|li|td|th|dd|dt|figcaption|label|blockquote|a|span)$/
            .test(parent.tagName.toLowerCase());
        if (s.display === 'inline' || (inText && s.display.startsWith('inline'))) return false;
        return true;
    });
    const rects = targets.map(el => el.getBoundingClientRect());
    const small = [];
    for (let i = 0; i < targets.length; i++) {
        const el = targets[i];
        const rect = rects[i];
        if (rect.width === 0 && rect.height === 0) continue;
        if (rect.width >= 44 && rect.height >= 44) continue;
        // Spacing-Ausnahme: 24px freier Raum rund um das Ziel (kein anderes Ziel).
        const zone = {
            left: rect.left - 24, right: rect.right + 24,
            top: rect.top - 24, bottom: rect.bottom + 24,
        };
        const overlapsOther = targets.some((other, j) => {
            if (j === i) return false;
            const r = rects[j];
            return r.left < zone.right && r.right > zone.left
                && r.top < zone.bottom && r.bottom > zone.top;
        });
        if (!overlapsOther) continue;
        const path = [];
        let cur = el;
        while (cur && cur !== document.body) {
            let t = cur.tagName.toLowerCase();
            if (cur.id) t += '#' + cur.id;
            else if (cur.className) t += '.' + cur.className.split(' ')[0];
            path.unshift(t);
            cur = cur.parentElement;
        }
        small.push({ tag: el.tagName.toLowerCase(), path: path.join(' > '),
                     w: Math.round(rect.width), h: Math.round(rect.height) });
    }
    return small;
}"""


async def check_target_size(ctx: CheckContext):
    """WCAG 2.5.5 — Touch-Zielgröße < 44 CSS-px (nur Auflösung ≤ 768px)."""
    if ctx.resolution is None or ctx.resolution > 768:
        return []
    page = ctx.page
    errors = []
    try:
        small = await page.evaluate(_TARGET_SIZE_JS)
    except Exception:
        return errors
    for info in small[:10]:
        errors.append(finding("WCAG_2_5_5_TARGET_SIZE",
                              f"<{info['tag']}> nur {info['w']}×{info['h']}px "
                              "(Mindestgröße 44×44px)",
                              info["path"]))
    return errors
