"""WCAG 2.4.7 — sichtbarer Fokus-Indikator (nur Desktop > 1160px, desktop_only).

Fixes (Review):
- Fokus per focus({ focusVisible: true }) setzen — programmatisches focus()
  setzt :focus, aber nicht :focus-visible (Massen-FP bei modernen Seiten).
- ::before/::after-Outline als Indikator ausgewertet (war toter Code).
- label[for='…']-Selektor gegen Seiten-Inhalts-Injection per CSS.escape
  geschützt.

Seit dem Batching-Umbau (Task Playwright-Batching): Vor-Prüfungen in EINEM
page.evaluate (_FOCUS_INDICATOR_BATCH_JS), die Fokusmessung mit Wartepausen in
gechunkten evaluates (_FOCUS_MEASURE_CHUNK_JS, _helpers). Der canFocus-Test ist
in die Messung integriert (focus({focusVisible:true}) → activeElement-Check).
"""
from __future__ import annotations

from ._base import CheckContext, finding
from ._helpers import (
    _FOCUS_CHUNK_SIZE,
    _FOCUS_INDICATOR_BATCH_JS,
    _FOCUS_MEASURE_CHUNK_JS,
    _style_changed,
)


async def check_focus_visible(ctx: CheckContext):
    """WCAG 2.4.7 — Tastaturfokus ohne sichtbaren Indikator."""
    page = ctx.page
    errors = []

    candidates = await page.evaluate(_FOCUS_INDICATOR_BATCH_JS)
    for start in range(0, len(candidates), _FOCUS_CHUNK_SIZE):
        chunk = candidates[start:start + _FOCUS_CHUNK_SIZE]
        results = await page.evaluate(_FOCUS_MEASURE_CHUNK_JS, chunk)
        by_index = {r["index"]: r for r in results}
        for cand in chunk:
            r = by_index.get(cand["index"])
            if r is None:
                continue
            try:
                changed = any(_style_changed(a, b) for a, b in zip(r["inactive"], r["focused"]))
            except Exception:
                continue  # wie im Original: Stil-Analyse-Fehler überspringt den Kandidaten
            if not changed:
                errors.append(finding("WCAG_2_4_7_FOCUS_INDICATOR",
                                      f"<{cand['node']}> ohne sichtbaren Fokus-Indikator",
                                      cand["path"]))
    return errors
