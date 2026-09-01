"""BITV 9.1.4.3 — Kontraste von Texten ausreichend.

Übernommen aus WCAG 1.4.3 (``wcag_1_4_3_contrast_aa.check_contrast_min``):
misst die Effektiv-Farben inkl. Alpha-Blending, Gradient-Token-Filter
(-webkit-text-fill-color, Element-opacity) und großer-Schrift-Schwelle
(14 pt fett = 18,66 px bzw. 18 pt = 24 px). Die Befunde verwenden die
BITV-Test-ID.

Manuelle Anteile des Prüfschritts (Styleswitcher-Prüfung, Sichtprüfung
feiner Schriften, Ausnahmen für native Browser-Elemente) bleiben außerhalb
der automatisierten Kontrastmessung.
"""
from __future__ import annotations

from ._base import CheckContext, finding
from ._helpers import (
    _deepest_text_elements,
    _is_large_text,
    contrast,
    parse_color,
)


async def check_kontraste_von_texten_ausreichend(ctx: CheckContext):
    """BITV 9.1.4.3 — Textkontrast: 4.5:1 (bzw. 3:1 großer Text)."""
    errors = []
    aa_threshold = 4.5
    for item in await _deepest_text_elements(ctx.page, ctx.resolution, ctx.url):
        path = item["path"]
        threshold = 3.0 if _is_large_text(item["fontSize"], item["isBold"]) else aa_threshold
        snippet = item["text"][:40].replace("\n", " ").replace("\t", " ")

        if item.get("contrastResults") and item["contrastResults"]["isGradient"]:
            worst = item["contrastResults"]["worstRatio"]
            if worst < threshold:
                errors.append(finding("BITV_9_1_4_3_KONTRASTE_VON_TEXTEN_AUSREICHEND",
                                      f"Gradient {worst:.2f}:1 (erfordert {threshold}:1) für '{snippet}…'",
                                      path, ctx.resolution))
        else:
            ratio = contrast(
                parse_color(item["foreground"]),
                parse_color(item["background"]),
            )
            if ratio < threshold:
                errors.append(finding("BITV_9_1_4_3_KONTRASTE_VON_TEXTEN_AUSREICHEND",
                                      f"{ratio:.2f}:1 (erfordert {threshold}:1) für '{snippet}…'",
                                      path, ctx.resolution))
    return errors
