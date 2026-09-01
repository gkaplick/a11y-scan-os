"""BITV_7_2_1_WIEDERGABE_VON_AUDIODESKRIPTION — Wiedergabe von Audiodeskription.

Quelle: docs/bitvtest/7.2.1.json (EN 301 549 7.2.1).

Der Prüfschritt ist anwendbar, wenn für Videos Alternativen mit
Audiodeskription bereitstehen: Dann muss es einen Mechanismus zur Auswahl und
Wiedergabe der Audiodeskription geben. Native Player (`controls`) bieten die
AD-Tonspur über die Spracheinstellungen an; ein Video mit AD-Spur, aber ohne
`controls` (benutzerdefinierter Player) lässt den Auswahlmechanismus nicht
erkennen und wird als Befund gemeldet.

Videos ohne AD-Spur sind nicht anwendbar (Abgrenzung zu 9.1.2.5, wo das
Fehlen der Audiodeskription selbst geprüft wird). Reine Gestaltungselemente
(stumm, ohne Bedienelemente) sind keine Player und ebenfalls übersprungen.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding, get_dom_path
from ._helpers import _media_elements, _media_has_ad, _media_ist_design_element

_BITV_TEST_ID = "BITV_7_2_1_WIEDERGABE_VON_AUDIODESKRIPTION"


async def check_wiedergabe_von_audiodeskription(ctx: CheckContext) -> list[Finding]:
    """BITV 7.2.1 — Video mit AD, deren Auswahl/Wiedergabe nicht erkennbar ist."""
    errors = []
    for video in _media_elements(ctx, kinds=("video",)):
        if _media_ist_design_element(video):
            continue
        if not _media_has_ad(video):
            # Keine Audiodeskription bereitgestellt → Prüfschritt nicht anwendbar
            continue
        if video.has_attr("controls"):
            continue
        errors.append(finding(
            _BITV_TEST_ID,
            "Video mit Audiodeskriptions-Spur, aber ohne erkennbaren "
            "Mechanismus zur Auswahl/Wiedergabe der Audiodeskription "
            "(kein native controls)",
            get_dom_path(video),
        ))
    return errors
