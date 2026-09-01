"""BITV_7_3_BEDIENELEMENTE_FUER_UNTERTITEL_UND_AUDIODESKRIPTION — Bedienelemente für Untertitel und Audiodeskription.

Quelle: docs/bitvtest/7.3.json (EN 301 549 7.3).

Der Prüfschritt gilt für Player mit Entwickler-definierten Bedienelementen,
die Videos mit zugehörigen Audioinhalten abspielen und Untertitel und/oder
Audiodeskription anbieten: Die CC-/AD-Bedienelemente müssen auf derselben
Interaktionsebene liegen wie die Wiedergabekontrolle. Bei nativen
Browser-Playern (`controls`) ist der Prüfschritt laut bitvtest.de nicht
anwendbar.

Automatisiert erkannt wird der anwendbare Fall (Video mit Untertitel-Spur
oder AD-Spur in einem benutzerdefinierten Player ohne `controls`) — ob die
Bedienelemente tatsächlich auf gleicher Ebene liegen, ist erst im UI
beurteilbar und wird als zu prüfender Befund gemeldet. Videos ohne
Untertitel/AD oder reine Gestaltungselemente (stumm, ohne Bedienelemente)
sind nicht anwendbar und werden übersprungen.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding, get_dom_path
from ._helpers import _media_elements, _media_has_ad, _media_has_captions, _media_ist_design_element

_BITV_TEST_ID = "BITV_7_3_BEDIENELEMENTE_FUER_UNTERTITEL_UND_AUDIODESKRIPTION"


async def check_bedienelemente_fuer_untertitel_und_audiodeskription(ctx: CheckContext) -> list[Finding]:
    """BITV 7.3 — CC-/AD-Bedienelemente im benutzerdefinierten Player zu prüfen."""
    errors = []
    for video in _media_elements(ctx, kinds=("video",)):
        if _media_ist_design_element(video):
            continue
        if not _media_has_captions(video) and not _media_has_ad(video):
            # Weder Untertitel noch Audiodeskription angeboten → nicht anwendbar
            continue
        if video.has_attr("controls"):
            # Nativer Browser-Player → Prüfschritt laut bitvtest.de nicht anwendbar
            continue
        errors.append(finding(
            _BITV_TEST_ID,
            "Video in benutzerdefiniertem Player mit Untertiteln/Audiodeskription — "
            "Bedienelemente für Untertitel und Audiodeskription müssen auf "
            "derselben Interaktionsebene liegen wie die Wiedergabekontrolle "
            "(manuell zu prüfen)",
            get_dom_path(video),
        ))
    return errors
