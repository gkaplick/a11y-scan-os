"""WCAG 1.4.3 (AA) — Kontrast: 4.5:1 (bzw. 3:1 für großen Text).

Nutzt den geteilten Farb-Kern (_helpers): Effektiv-Farben inkl. Alpha-Blending,
Gradient-Token-Filter (kein linear/to/right-Massen-FP), -webkit-text-fill-color
und Element-opacity; große-Schrift-Schwelle 14 pt fett (18,66 px).
"""
from __future__ import annotations

from ._base import CheckContext, finding
from ._helpers import (
    _deepest_text_elements,
    _is_large_text,
    contrast,
    parse_color,
)


async def check_contrast_min(ctx: CheckContext):
    """WCAG 1.4.3 (AA) — Textkontrast: 4.5:1 (bzw. 3:1 großer Text)."""
    errors = []
    aa_threshold = 4.5
    for item in await _deepest_text_elements(ctx.page, ctx.resolution, ctx.url):
        path = item["path"]
        threshold = 3.0 if _is_large_text(item["fontSize"], item["isBold"]) else aa_threshold
        snippet = item["text"][:40].replace("\n", " ").replace("\t", " ")

        if item.get("contrastResults") and item["contrastResults"]["isGradient"]:
            worst = item["contrastResults"]["worstRatio"]
            if worst < threshold:
                errors.append(finding("WCAG_1_4_3_CONTRAST_AA",
                                      f"Gradient {worst:.2f}:1 (erfordert {threshold}:1) für '{snippet}…'",
                                      path, ctx.resolution))
        else:
            ratio = contrast(
                parse_color(item["foreground"]),
                parse_color(item["background"]),
            )
            if ratio < threshold:
                errors.append(finding("WCAG_1_4_3_CONTRAST_AA",
                                      f"{ratio:.2f}:1 (erfordert {threshold}:1) für '{snippet}…'",
                                      path, ctx.resolution))
    return errors
