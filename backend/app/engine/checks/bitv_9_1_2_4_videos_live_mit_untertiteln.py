"""BITV_9_1_2_4_VIDEOS_LIVE_MIT_UNTERTITELN — Videos (live) mit Untertiteln.

Quelle: docs/bitvtest/9.1.2.4.json (WCAG 1.2.4, Level AA).

Automatisiert prüfbar ist die Untertitel-Spur von Live-Streams: Videos, deren
Quelle auf einen Live-/Adaptiv-Stream hinweist (HLS *.m3u8/*.m3u, MPEG-DASH
*.mpd), benötigen eine Untertitel-Alternative, sobald die Tonspur Information
trägt. Videos ohne solche Stream-Quelle sind für diesen Prüfschritt nicht
eindeutig als Live erkennbar und werden übersprungen (Abgrenzung zu
BITV_9.1.2.2 "Aufgezeichnete Videos mit Untertiteln").

Reine Gestaltungselemente (stumm, ohne Bedienelemente) brauchen keine
Untertitel und werden ebenfalls übersprungen — ebenso Live-Videos mit
funktionierender Untertitel-Spur (kind="captions").
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding, get_dom_path
from ._helpers import (
    _media_elements,
    _media_has_captions,
    _media_ist_design_element,
    _media_ist_live_stream,
)

_BITV_TEST_ID = "BITV_9_1_2_4_VIDEOS_LIVE_MIT_UNTERTITELN"


async def check_videos_live_mit_untertiteln(ctx: CheckContext) -> list[Finding]:
    """BITV 9.1.2.4 — Live-Stream-Video ohne Untertitel-Spur (kind="captions")."""
    errors = []
    for video in _media_elements(ctx, kinds=("video",)):
        if _media_ist_design_element(video):
            continue
        if not _media_ist_live_stream(video):
            continue
        if _media_has_captions(video):
            continue
        errors.append(finding(
            _BITV_TEST_ID,
            "Live-Stream-Video ohne Untertitel-Spur (kind=\"captions\")",
            get_dom_path(video),
        ))
    return errors
