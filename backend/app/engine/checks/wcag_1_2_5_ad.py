"""WCAG 1.2.5 — Audiodeskription für aufgezeichnetes Video.

Geteilter Algorithmus mit EN_7_2_1_AD_PLAYBACK (en_7_2_1_ad_playback.py) —
der Runner setzt ctx.test_id, damit das Finding dem richtigen Kriterium
zugeordnet wird.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import _media_has_ad, _media_ist_design_element


async def check_ad_playback(ctx: CheckContext):
    """WCAG 1.2.5 — Video ohne Audiodeskriptions-Spur."""
    errors = []
    for video in ctx.soup.find_all("video"):
        if not is_accessible_element(video):
            continue
        # Reines Gestaltungselement (stumm, ohne Bedienelemente) hat keinen
        # gesprochenen Inhalt, für den Audiodeskription nötig wäre.
        if _media_ist_design_element(video):
            continue
        if not _media_has_ad(video):
            errors.append(finding("WCAG_1_2_5_AD",
                                  "Video ohne Audiodeskriptions-Spur", get_dom_path(video)))
    return errors
