"""BITV_9_1_4_10_INHALTE_BRECHEN_UM — Inhalte brechen um.

Prüfschritt 9.1.4.10 (WCAG 1.4.10 Reflow): Seiten-Inhalte sollen bei einer
Browserfensterbreite von 320 CSS-Pixeln (bzw. bei 1280 px und 400 % Zoom) so
umbrechen, dass alle Informationen und Funktionen ohne horizontales Scrollen
verfügbar sind.

Automatisierbar sind drei Kern-Bedingungen (übernommen aus den WCAG-Checks
1.4.10 VIEWPORT_ZOOM / VIEWPORT_MISSING / REFLOW):

- viewport-Meta-Tag vorhanden (Basis responsiver Umbrüche),
- Zoomen nicht blockiert (``user-scalable=no`` / ``maximum-scale`` ≤ 1),
- kein horizontaler Überlauf im schmalen Viewport (≤ 768 px).

Die viewport-Meta-Prüfung läuft rein über das Soup-DOM und damit in jedem
Modus. Die Überlauf-Prüfung benötigt eine gerenderte Seite (ctx.page) und läuft
nur, wenn der Check mit Seite ausgeführt wird (Resolution-Modus). Die visuelle
Bewertung, ob Inhalte tatsächlich ohne Verlust umbrechen, bleibt im Detail eine
manuelle Prüfung (Ausnahmen: Datentabellen, Diagramme, Videos, Werkzeugleisten …).
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path

_TEST_ID = "BITV_9_1_4_10_INHALTE_BRECHEN_UM"

_REFLOW_JS = """() => {
    const doc = document.documentElement;
    let scrollWidth = doc.scrollWidth;
    const clientWidth = doc.clientWidth;
    for (const frame of document.querySelectorAll('iframe')) {
        try {
            const rect = frame.getBoundingClientRect();
            if (rect.right > clientWidth) {
                scrollWidth = Math.max(scrollWidth, rect.right);
            }
        } catch (e) { /* cross-origin */ }
    }
    return { scrollWidth, clientWidth };
}"""


def _viewport_meta(soup):
    """viewport-Meta-Tag aus dem Soup-DOM (Namens-Vergleich case-insensitiv)."""
    if soup is None:
        return None
    for meta in soup.find_all("meta"):
        if (meta.get("name") or "").strip().lower() == "viewport":
            return meta
    return None


def _viewport_content(soup) -> tuple[bool, str]:
    """(vorhanden, content) des viewport-Meta-Tags aus dem Soup-DOM."""
    meta = _viewport_meta(soup)
    if meta is None:
        return False, ""
    return True, (meta.get("content") or "").lower()


async def check_inhalte_brechen_um(ctx: CheckContext):
    """BITV_9_1_4_10_INHALTE_BRECHEN_UM — Inhalte brechen um."""
    errors = []

    # 1. viewport-Meta-Tag vorhanden? (funktioniert in jedem Modus)
    has_viewport, content = _viewport_content(ctx.soup)
    if not has_viewport:
        errors.append(finding(
            _TEST_ID,
            "Kein viewport-Meta-Tag gefunden — responsive Umbrüche gefährdet",
            "head",
        ))
    else:
        # 2. Zoomen nicht blockiert?
        max_scale_match = re.search(r"maximum-scale\s*=\s*([\d.]+)", content)
        max_scale = float(max_scale_match.group(1)) if max_scale_match else None
        if "user-scalable=no" in content:
            reason = "user-scalable=no"
        elif max_scale is not None and max_scale <= 1:
            reason = f"maximum-scale={max_scale} (≤ 1)"
        else:
            reason = None
        if reason:
            meta = _viewport_meta(ctx.soup)
            errors.append(finding(
                _TEST_ID,
                f"Zoomen blockiert: {reason} in viewport-Meta",
                get_dom_path(meta) if meta is not None else "head > meta[name=viewport]",
            ))

    # 3. Kein horizontaler Überlauf im schmalen Viewport (nur mit gerenderter Seite)
    if ctx.page is not None and ctx.resolution is not None and ctx.resolution <= 768:
        try:
            dims = await ctx.page.evaluate(_REFLOW_JS)
            if dims["scrollWidth"] > dims["clientWidth"]:
                width = dims["clientWidth"]
                errors.append(finding(
                    _TEST_ID,
                    f"Horizontaler Überlauf: Dokument {dims['scrollWidth']}px "
                    f"breiter als Viewport {width}px",
                    "html",
                    resolution=ctx.resolution,
                ))
        except Exception:
            pass

    return errors
