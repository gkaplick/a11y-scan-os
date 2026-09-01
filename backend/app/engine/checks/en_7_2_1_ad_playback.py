"""EN 301 549 7.2.1 — Wiedergabe von Audiodeskription möglich.

Geteilter Algorithmus mit WCAG_1_2_5_AD (wcag_1_2_5_ad.py) — der Runner setzt
ctx.test_id, damit das Finding dem richtigen Kriterium zugeordnet wird.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import _media_has_ad, _media_ist_design_element


async def check_ad_playback(ctx: CheckContext):
    """EN 7.2.1 — Video ohne Audiodeskriptions-Spur."""
    errors = []
    for video in ctx.soup.find_all("video"):
        if not is_accessible_element(video):
            continue
        # Reines Gestaltungselement (stumm, ohne Bedienelemente) hat keinen
        # gesprochenen Inhalt, für den Audiodeskription nötig wäre.
        if _media_ist_design_element(video):
            continue
        if not _media_has_ad(video):
            errors.append(finding("EN_7_2_1_AD_PLAYBACK",
                                  "Video ohne Audiodeskriptions-Spur", get_dom_path(video)))
    return errors
