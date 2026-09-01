"""WCAG 1.4.2 — Audio wird nicht automatisch abgespielt.

Fix (Review): autoplay/muted sind Boolean-Attribute — <video autoplay> hat den
Wert "". get("autoplay") lieferte "" (falsy) → der Check feuerte nie. has_attr()
prüft die Anwesenheit korrekt.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element


async def check_autoplay(ctx: CheckContext):
    """WCAG 1.4.2 — Video mit autoplay ohne muted, bzw. Audio mit autoplay."""
    errors = []
    for video in ctx.soup.find_all("video"):
        if is_accessible_element(video) and video.has_attr("autoplay") and not video.has_attr("muted"):
            errors.append(finding("WCAG_1_4_2_AUTOPLAY",
                                  "Video mit autoplay ohne muted", get_dom_path(video)))
    for audio in ctx.soup.find_all("audio"):
        if is_accessible_element(audio) and audio.has_attr("autoplay"):
            errors.append(finding("WCAG_1_4_2_AUTOPLAY",
                                  "Audio mit autoplay", get_dom_path(audio)))
    return errors
