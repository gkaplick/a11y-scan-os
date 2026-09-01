"""BITV_7_1_1_WIEDERGABE_VON_UNTERTITELN — Wiedergabe von Untertiteln.

Quelle: docs/bitvtest/7.1.1.json (EN 301 549 7.1.1).

Der Prüfschritt ist anwendbar, wenn Videos mit Untertiteln vorhanden sind:
Dann muss der Player Untertitel ein-/ausblenden können. Native
Videoplayer (`controls`) stellen dafür einen Browser-Bedienknopf bereit; ein
Video mit Untertitel-Spur, aber ohne `controls` (benutzerdefinierter Player)
lässt die Zuschaltbarkeit nicht erkennen und wird als Befund gemeldet.

Videos ohne Untertitel-Spur sind für diesen Prüfschritt nicht anwendbar und
werden übersprungen (Abgrenzung zu 9.1.2.2, wo das Fehlen der Untertitel
selbst geprüft wird). Reine Gestaltungselemente (stumm, ohne Bedienelemente)
sind keine Player und ebenfalls übersprungen.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding, get_dom_path
from ._helpers import _media_elements, _media_has_captions, _media_ist_design_element

_BITV_TEST_ID = "BITV_7_1_1_WIEDERGABE_VON_UNTERTITELN"


async def check_wiedergabe_von_untertiteln(ctx: CheckContext) -> list[Finding]:
    """BITV 7.1.1 — Video mit Untertiteln, deren Ein-/Ausblenden nicht möglich ist."""
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
            _BITV_TEST_ID,
            "Video mit Untertitel-Spur, aber ohne erkennbares Bedienelement "
            "zum Ein-/Ausblenden der Untertitel (kein native controls)",
            get_dom_path(video),
        ))
    return errors
