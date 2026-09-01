"""WCAG 1.2.1 — Textalternative (Transkript) für reine Audio-/Video-Inhalte.

Fix (Review): auch <video> einbeziehen (Video ohne Sprachspur / mit Tonspur
braucht eine Textalternative) und deutsche Alternativen-Keywords erweitern.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_KEYWORDS = ("transkript", "transcript", "abschrift", "wortprotokoll")


async def check_audio_transcript(ctx: CheckContext):
    """WCAG 1.2.1 — Audio/Video ohne verlinktes Transkript."""
    errors = []
    for media in ctx.soup.find_all(["audio", "video"]):
        if not is_accessible_element(media):
            continue
        parent = media.find_parent()
        transcript_nearby = False
        if parent:
            transcript_links = parent.find_all("a", href=True)
            transcript_nearby = any(
                any(w in (link.get_text() or "").lower() for w in _KEYWORDS)
                or any(w in (link.get("title") or "").lower() for w in _KEYWORDS)
                or any(w in (link.get("aria-label") or "").lower() for w in _KEYWORDS)
                for link in transcript_links
            )
            if not transcript_nearby:
                describedby = media.get("aria-describedby")
                if describedby:
                    el = parent.find(id=describedby)
                    if el and any(w in (el.get_text() or "").lower() for w in _KEYWORDS):
                        transcript_nearby = True
        if not transcript_nearby:
            errors.append(finding("WCAG_1_2_1_AUDIO_TRANSCRIPT",
                                  f"<{media.name}> ohne verlinktes Transkript",
                                  get_dom_path(media)))
    return errors
