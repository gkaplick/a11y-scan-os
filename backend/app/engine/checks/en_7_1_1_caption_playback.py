"""EN_7_1_1_CAPTION_PLAYBACK — Wiedergabe von Untertiteln.

Quelle: EN 301 549 7.1.1 (Kap. 7, "Kommunikationstechnik mit Videofunktionen").

Geteilter Algorithmus mit BITV_7_1_1_WIEDERGABE_VON_UNTERTITELN
(bitv_7_1_1_wiedergabe_von_untertiteln.py) — der Runner setzt ctx.test_id,
damit das Finding dem richtigen Kriterium zugeordnet wird.

Ein Video mit Untertitel-Spur (kind="captions") muss der Nutzerin ein- und
ausblenden können: Native Player (`controls`) bieten dafür einen
Browser-Bedienknopf; ohne `controls` ist die Zuschaltbarkeit nicht erkennbar
und wird als Befund gemeldet. Videos ohne Untertitel-Spur sind nicht
anwendbar, reine Gestaltungselemente (stumm, ohne Bedienelemente) sind keine
Player und werden übersprungen.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding, get_dom_path
from ._helpers import _media_elements, _media_has_captions, _media_ist_design_element

_EN_TEST_ID = "EN_7_1_1_CAPTION_PLAYBACK"


async def check_caption_playback(ctx: CheckContext) -> list[Finding]:
    """EN 7.1.1 — Video mit Untertiteln, deren Ein-/Ausblenden nicht möglich ist."""
    errors = []
    for video in _media_elements(ctx, kinds=("video",)):
        if _media_ist_design_element(video):
            continue
        if not _media_has_captions(video):
            # Keine Untertitel angeboten → Prüfschritt nicht anwendbar
            continue
        if video.has_attr("controls"):
            continue
        errors.append(finding(
            _EN_TEST_ID,
            "Video mit Untertitel-Spur, aber ohne erkennbares Bedienelement "
            "zum Ein-/Ausblenden der Untertitel (kein native controls)",
            get_dom_path(video),
        ))
    return errors
