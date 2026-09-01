"""BITV 9.1.2.3 — Audiodeskription oder Volltext-Alternative für Videos.

Tonbehaftete Videos (nicht ``muted``) brauchen entweder eine
Audiodeskriptions-Spur (<track kind="descriptions">) oder eine
Volltext-Alternative (Transkript) — das WCAG-1.2.3-Niveau (A), das die
Volltext-Option erlaubt. Die strengere WCAG-1.2.5-Variante (nur AD) ist
BITV 9.1.2.5.

Stumme Videos fallen unter 9.1.2.1, Untertitel unter 9.1.2.2. Eine reine
Untertitel-Spur (kind="captions") ist keine Audiodeskription.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import _media_has_ad, _media_has_transcript

_TEST_ID = "BITV_9_1_2_3_AUDIODESKRIPTION_ODER_VOLLTEXT_ALTERNATIVE_FUER_VIDEOS"


async def check_audiodeskription_oder_volltext_alternative_fuer_videos(ctx: CheckContext):
    """BITV 9.1.2.3 — Video ohne Audiodeskription und ohne Volltext-Alternative."""
    errors = []
    for video in ctx.soup.find_all("video"):
        if not is_accessible_element(video):
            continue
        # Stumme Videos brauchen keine Audiodeskription (→ 9.1.2.1).
        if video.get("muted") is not None:
            continue
        if _media_has_ad(video):
            continue
        if _media_has_transcript(video, ctx.soup):
            continue
        errors.append(finding(
            _TEST_ID,
            "Video ohne Audiodeskription und ohne Volltext-Alternative",
            get_dom_path(video),
        ))
    return errors
