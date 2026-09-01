"""BITV 9.1.2.5 — Audiodeskription für Videos.

Die Audiodeskription wird über
eine funktionierende <track kind="descriptions">-Spur (mit src) nachgewiesen
(Helfer _media_has_ad).

Videos, die als Medienalternative zu einem textbasierten Inhalt dienen, keine
Tonspur haben oder deren Bildgeschehen nicht in Worte gefasst werden kann,
brauchen keine Audiodeskription — diese Ausnahmen lassen sich automatisiert
nicht zuverlässig erkennen und bleiben der manuellen Bewertung überlassen.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding, get_dom_path, is_accessible_element
from ._helpers import _media_has_ad, _media_ist_design_element

_TEST_ID = "BITV_9_1_2_5_AUDIODESKRIPTION_FUER_VIDEOS"


async def check_audiodeskription_fuer_videos(ctx: CheckContext) -> list[Finding]:
    """BITV 9.1.2.5 — Video ohne Audiodeskriptions-Spur."""
    errors = []
    for video in ctx.soup.find_all("video"):
        if not is_accessible_element(video):
            continue
        # Reines Gestaltungselement (stumm, ohne Bedienelemente) hat keinen
        # gesprochenen Inhalt, für den Audiodeskription nötig wäre.
        if _media_ist_design_element(video):
            continue
        if not _media_has_ad(video):
            errors.append(finding(
                _TEST_ID,
                "Video ohne Audiodeskriptions-Spur (track kind=\"descriptions\")",
                get_dom_path(video),
            ))
    return errors
