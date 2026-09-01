"""WCAG 1.2.3 — Audiodeskription oder Medienalternative (voraufgezeichnet).

Port des implementierten BITV-Checks 9.1.2.3 (gleicher Algorithmus,
anderer test_id). Tonbehaftete Videos (nicht ``muted``) brauchen entweder
eine Audiodeskriptions-Spur (<track kind="descriptions">) oder eine
Volltext-Alternative (Transkript) — das WCAG-1.2.3-Niveau (A), das die
Volltext-Option erlaubt. Die strengere WCAG-1.2.5-Variante (nur AD) ist
separat implementiert.

Stumme Videos fallen unter 1.2.1, Untertitel unter 1.2.2. Eine reine
Untertitel-Spur (kind="captions") ist keine Audiodeskription.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import _media_has_ad, _media_has_transcript

_TEST_ID = "WCAG_1_2_3_AD_MEDIA_ALT"


async def check_ad_media_alt(ctx: CheckContext):
    """WCAG 1.2.3 — Video ohne Audiodeskription und ohne Volltext-Alternative."""
    errors = []
    for video in ctx.soup.find_all("video"):
        if not is_accessible_element(video):
            continue
        # Stumme Videos brauchen keine Audiodeskription (→ 1.2.1).
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
