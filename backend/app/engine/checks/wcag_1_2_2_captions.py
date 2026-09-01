"""WCAG 1.2.2 — Untertitel (Captions) für aufgezeichnetes Video.

Fix (Review): Nur kind="captions" ist eine Untertitel-Alternative —
kind="subtitles" ist eine Übersetzung ohne Geräusche-Information. Ein
<track> ohne src liefert keine Untertitel.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import _media_has_captions, _media_ist_design_element


async def check_video_captions(ctx: CheckContext):
    """WCAG 1.2.2 — Video ohne funktionierende Untertitel-Spur (kind="captions")."""
    errors = []
    for video in ctx.soup.find_all("video"):
        if not is_accessible_element(video):
            continue
        # Reines Gestaltungselement (stumm, ohne Bedienelemente) hat keinen
        # gesprochenen Inhalt, für den Untertitel nötig wären.
        if _media_ist_design_element(video):
            continue
        if not _media_has_captions(video):
            errors.append(finding("WCAG_1_2_2_CAPTIONS",
                                  "Video ohne Untertitel-Spur", get_dom_path(video)))
    return errors
