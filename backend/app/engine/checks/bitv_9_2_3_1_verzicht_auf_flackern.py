"""BITV 9.2.3.1 — Verzicht auf Flackern.

WCAG 2.3.1: Seiteninhalte blitzen nicht häufiger als dreimal pro Sekunde.
Statisch erkennbar sind die klassischen Fehlerfälle:
- das veraltete <blink>-Element (F7),
- `text-decoration: blink` in style-Attributen und <style>-Blöcken (F4).

CSS-@keyframes-/Animationen mit hoher Frequenz und per JS getaktete Blitze
sind statisch nicht frequenzbewertbar — dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_2_3_1_VERZICHT_AUF_FLACKERN"

# text-decoration: blink — mit beliebigem Weißraum davor/danach (F4)
_BLINK_DECORATION = re.compile(
    r"""text-decoration\s*:\s*[^;}]*\bblink\b""",
    re.IGNORECASE,
)


async def check_verzicht_auf_flackern(ctx: CheckContext):
    """BITV 9.2.3.1 — Blink-Elemente/Blink-Decoration (Flackern > 3×/s)."""
    errors = []

    for el in ctx.soup.find_all("blink"):
        if is_accessible_element(el):
            errors.append(finding(
                _TEST_ID,
                "<blink>-Element blitzt permanent auf (Flackern > 3×/s)",
                get_dom_path(el),
            ))

    for el in ctx.soup.find_all(style=True):
        if not is_accessible_element(el):
            continue
        if _BLINK_DECORATION.search(el.get("style", "")):
            errors.append(finding(
                _TEST_ID,
                f"text-decoration: blink im style-Attribut von <{el.name}> "
                "(Flackern > 3×/s)",
                get_dom_path(el),
            ))

    for style_block in ctx.soup.find_all("style"):
        if _BLINK_DECORATION.search(style_block.get_text() or ""):
            errors.append(finding(
                _TEST_ID,
                "text-decoration: blink im <style>-Block (Flackern > 3×/s)",
                get_dom_path(style_block),
            ))

    return errors[:10]
