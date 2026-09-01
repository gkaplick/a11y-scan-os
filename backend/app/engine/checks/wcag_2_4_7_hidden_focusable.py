"""WCAG 2.4.7 — kein verstecktes fokussierbares Element (Desktop > 1160px).

Fixes (Review):
- display:none-Vorfahren über el.offsetParent erkannt (nicht vererbbar) →
  solche Elemente sind nicht fokussierbar und kein Befund (kein FP).
- opacity:0 aus dem Skip entfernt — ein opacity:0-Element ist fokussierbar,
  aber unsichtbar → Befund (kein FN).
- handles[:10]-Cap entfernt.

Seit dem Batching-Umbau: Skip-Vorprüfung in EINEM evaluate
(_HIDDEN_FOCUSABLE_BATCH_JS), Fokustest gechunkt (_HIDDEN_FOCUS_CHUNK_JS).
"""
from __future__ import annotations

from ._base import CheckContext, finding
from ._helpers import (
    _FOCUS_CHUNK_SIZE,
    _HIDDEN_FOCUSABLE_BATCH_JS,
    _HIDDEN_FOCUS_CHUNK_JS,
)


async def check_hidden_focusable(ctx: CheckContext):
    """WCAG 2.4.7 — unsichtbares Element kann per Tastatur fokussiert werden."""
    page = ctx.page
    errors = []

    candidates = await page.evaluate(_HIDDEN_FOCUSABLE_BATCH_JS)
    for start in range(0, len(candidates), _FOCUS_CHUNK_SIZE):
        chunk = candidates[start:start + _FOCUS_CHUNK_SIZE]
        for info in await page.evaluate(_HIDDEN_FOCUS_CHUNK_JS, chunk):
            desc = info["tagName"]
            if info["id"]:
                desc += f"#{info['id']}"
            elif info["className"]:
                desc += f".{info['className'].split(' ')[0]}"
            errors.append(finding("WCAG_2_4_7_HIDDEN_FOCUSABLE",
                                  f"{desc} fokussierbar, aber nicht sichtbar "
                                  f"(display={info['display']}, opacity={info['opacity']})",
                                  info["path"]))
    return errors
