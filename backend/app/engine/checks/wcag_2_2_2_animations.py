"""WCAG 2.2.2 — Anhalten, Beenden, Ausblenden (bewegte Inhalte abschaltbar).

Gleiche Regel wie BITV 9.2.2.2: Bewegende, blinkende oder
selbstaktualisierende Inhalte, die länger als 5 Sekunden laufen, brauchen
einen Abschalt-/Pause-/Ausblend-Mechanismus (F16/F47).

Erkennt im statischen DOM:
- veraltete Bewegungs-Elemente <marquee> und <blink> (F16),
- unendliche CSS-Animationen in style-Attributen und <style>-Blöcken
  (animation-iteration-count: infinite bzw. animation: … infinite, F47).

Liegt bewegter Inhalt vor, wird nach einem Abschalt-Mechanismus gesucht
(Button/Link/Bedienelement mit Pause-/Stop-/Anhalt-Beschriftung). Externe
Stylesheets und per JS animierte Inhalte sind statisch nicht sichtbar —
dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "WCAG_2_2_2_ANIMATIONS"

# animation: … infinite … bzw. animation-iteration-count: infinite
_INFINITE_ANIMATION = re.compile(
    r"""animation\s*:\s*[^;}]*?\binfinite\b|animation-iteration-count\s*:\s*infinite""",
    re.IGNORECASE,
)
# Wortstämme ohne Endgrenze: "pause" matcht auch "pausieren"/"Pause-Button".
_PAUSE = re.compile(
    r"""\b(pause|pausier|stopp|stop|anhalt|unterbrech)""", re.IGNORECASE
)
_MECHANISMUS_SELEKTOR = ("button", "a")


def _beschriftung(el) -> str:
    """Text-/aria-/title-Beschriftung eines Bedienelements."""
    return " ".join(filter(None, (
        el.get_text(strip=True),
        el.get("aria-label"),
        el.get("title"),
        el.get("value") if el.name == "input" else None,
    )))


async def check_animations(ctx: CheckContext):
    """WCAG 2.2.2 — Bewegter Inhalt ohne Abschalt-/Pause-Mechanismus."""
    bewegt: list[tuple] = []

    for el in ctx.soup.find_all(["marquee", "blink"]):
        if is_accessible_element(el):
            bewegt.append((el, f"<{el.name}>-Element mit automatischer Bewegung"))

    for el in ctx.soup.find_all(style=True):
        if not is_accessible_element(el):
            continue
        if _INFINITE_ANIMATION.search(el.get("style", "")):
            bewegt.append((el, f"Unendliche CSS-Animation im style-Attribut von <{el.name}>"))

    for style_block in ctx.soup.find_all("style"):
        if _INFINITE_ANIMATION.search(style_block.get_text() or ""):
            bewegt.append((style_block, "Unendliche CSS-Animation im <style>-Block"))

    if not bewegt:
        return []

    # Abschalt-/Pause-Mechanismus irgendwo auf der Seite?
    mechanismus = any(
        is_accessible_element(c) and _PAUSE.search(_beschriftung(c))
        for c in ctx.soup.find_all(_MECHANISMUS_SELEKTOR)
    )
    if mechanismus:
        return []

    errors = []
    for el, msg in bewegt[:10]:
        errors.append(finding(
            _TEST_ID,
            f"{msg} ohne Abschalt-/Pause-Mechanismus",
            get_dom_path(el),
        ))
    return errors
