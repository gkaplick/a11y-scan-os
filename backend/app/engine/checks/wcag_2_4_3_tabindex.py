"""WCAG 2.4.3 — Fokus-Reihenfolge: positiver tabindex stört die Tab-Reihenfolge.

Nur Desktop > 1160px (desktop_only).
"""
from __future__ import annotations

from ._base import CheckContext, finding
from ._helpers import DOM_PATH_JS

# Elemente mit positivem tabindex in EINEM evaluate statt je Element
# get_attribute + DOM_PATH_JS + tagName.
_BATCH_JS = (
    "() => {\n"
    "    const domPath = " + DOM_PATH_JS + ";\n"
    "    const out = [];\n"
    "    for (const el of document.querySelectorAll('[tabindex]')) {\n"
    "        const value = el.getAttribute('tabindex');\n"
    "        if (value && /^\\d+$/.test(value) && parseInt(value, 10) > 0) {\n"
    "            out.push({ path: domPath(el), tag: el.tagName.toLowerCase(), value });\n"
    "        }\n"
    "    }\n"
    "    return out;\n"
    "}"
)


async def check_tabindex(ctx: CheckContext):
    """WCAG 2.4.3 — Elemente mit positivem tabindex-Wert."""
    errors = []
    try:
        for item in await ctx.page.evaluate(_BATCH_JS):
            errors.append(finding(
                "WCAG_2_4_3_TABINDEX",
                f"Element '{item['tag']}' hat positiven tabindex-Wert ({item['value']}) — "
                "stört die natürliche Tab-Reihenfolge",
                item["path"],
            ))
    except Exception:
        pass
    return errors
