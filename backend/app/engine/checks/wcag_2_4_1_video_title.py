"""WCAG 2.4.1 — Video-Einbettungen (YouTube, Vimeo, …) mit iframe-Titel.

Fix (Review): Host-Vergleich per urlparse.netloc statt Substring — sonst
matcht "youtube.com" auch in "notyoutube.com" (Massen-FP).
"""
from __future__ import annotations

from urllib.parse import urlparse

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_VIDEO_DOMAINS = {
    "youtube.com", "youtu.be", "youtube-nocookie.com",
    "vimeo.com", "player.vimeo.com",
    "dailymotion.com", "dai.ly",
    "twitch.tv", "player.twitch.tv",
    "facebook.com", "fb.watch",
    "instagram.com", "instagr.am",
    "tiktok.com", "vm.tiktok.com",
}


def _is_video_host(src: str) -> bool:
    try:
        host = (urlparse(src).netloc or "").lower()
    except ValueError:
        return False
    return any(host == d or host.endswith("." + d) for d in _VIDEO_DOMAINS)


async def check_video_title(ctx: CheckContext):
    """WCAG 2.4.1 — eingebettetes Video ohne iframe-title-Attribut."""
    errors = []
    for iframe in ctx.soup.find_all("iframe"):
        if not is_accessible_element(iframe):
            continue
        src = iframe.get("src", "")
        if _is_video_host(src) and not iframe.get("title", "").strip():
            errors.append(finding("WCAG_2_4_1_VIDEO_TITLE",
                                  f"src='{src}'", get_dom_path(iframe)))
    return errors
