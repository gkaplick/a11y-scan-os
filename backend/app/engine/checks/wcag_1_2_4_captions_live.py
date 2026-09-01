"""WCAG_1_2_4_CAPTIONS_LIVE — Untertitel (Live).

Geteilter Algorithmus mit BITV_9_1_2_4_VIDEOS_LIVE_MIT_UNTERTITELN
(bitv_9_1_2_4_videos_live_mit_untertiteln.py): Live-/Adaptiv-Stream-Videos
(HLS *.m3u8/*.m3u, MPEG-DASH *.mpd) brauchen eine Untertitel-Spur
(kind="captions"). Videos ohne solche Stream-Quelle sind nicht eindeutig als
Live erkennbar und werden übersprungen; reine Gestaltungselemente (stumm,
ohne Bedienelemente) brauchen keine Untertitel.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path
from ._helpers import (
    _media_elements,
    _media_has_captions,
    _media_ist_design_element,
    _media_ist_live_stream,
)

_TEST_ID = "WCAG_1_2_4_CAPTIONS_LIVE"


async def check_captions_live(ctx: CheckContext):
    """WCAG 1.2.4 — Live-Stream-Video ohne Untertitel-Spur (kind="captions")."""
    errors = []
    for video in _media_elements(ctx, kinds=("video",)):
        if _media_ist_design_element(video):
            continue
        if not _media_ist_live_stream(video):
            continue
        if _media_has_captions(video):
            continue
        errors.append(finding(
            _TEST_ID,
            "Live-Stream-Video ohne Untertitel-Spur (kind=\"captions\")",
            get_dom_path(video),
        ))
    return errors
