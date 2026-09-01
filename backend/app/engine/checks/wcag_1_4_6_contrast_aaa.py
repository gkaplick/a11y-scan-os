"""WCAG 1.4.6 (AAA) — Kontrast: 7:1 (bzw. 4.5:1 für großen Text).

Nutzt den geteilten Farb-Kern (_helpers) — identische Basis wie der
AA-Kontrast-Check (wcag_1_4_3_contrast_aa.py), nur andere Schwellen.
"""
from __future__ import annotations

from ._base import CheckContext, finding
from ._helpers import (
    _deepest_text_elements,
    _is_large_text,
    contrast,
    parse_color,
)


async def check_contrast_aaa(ctx: CheckContext):
    """WCAG 1.4.6 (AAA) — Kontrast: 7:1 (bzw. 4.5:1 großer Text)."""
    errors = []
    for item in await _deepest_text_elements(ctx.page, ctx.resolution, ctx.url):
        path = item["path"]
        threshold = 4.5 if _is_large_text(item["fontSize"], item["isBold"]) else 7.0
        snippet = item["text"][:40].replace("\n", " ").replace("\t", " ")

        if item.get("contrastResults") and item["contrastResults"]["isGradient"]:
            worst = item["contrastResults"]["worstRatio"]
            if worst < threshold:
                errors.append(finding("WCAG_1_4_6_CONTRAST_AAA",
                                      f"Gradient {worst:.2f}:1 (erfordert {threshold}:1) für '{snippet}…'",
                                      path, ctx.resolution))
        else:
            ratio = contrast(
                parse_color(item["foreground"]),
                parse_color(item["background"]),
            )
            if ratio < threshold:
                errors.append(finding("WCAG_1_4_6_CONTRAST_AAA",
                                      f"{ratio:.2f}:1 (erfordert {threshold}:1) für '{snippet}…'",
                                      path, ctx.resolution))
    return errors
