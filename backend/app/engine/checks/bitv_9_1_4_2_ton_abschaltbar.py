"""BITV_9_1_4_2_TON_ABSCHALTBAR — Ton abschaltbar.

Prüfschritt 9.1.4.2 (bitvtest.de): Automatisch abgespielte Töne, die nicht nach
drei Sekunden enden, müssen über einen barrierefreien Mechanismus am
Seitenbeginn abgeschaltet oder heruntergeregelt werden können. Töne, die
automatisch enden (G60) oder nur auf Nutzeraktion starten (G171), sind erlaubt.

Automatisierbar (F93 — Abwesenheit einer Pause-/Stopp-Möglichkeit bei
autoplay):
- ``<audio autoplay>`` ohne ``muted`` → Ton startet automatisch beim Laden
- ``<video autoplay>`` ohne ``muted`` → Ton startet automatisch beim Laden
  (gestummte Wiedergabe erzeugt keinen Ton und ist kein Befund)

Nicht automatisierbar: die Dauer des Tons (> 3 Sekunden) sowie Existenz,
Position und Bedienbarkeit eines Abschalt-/Regler-Mechanismus am Seitenbeginn
(manuelle Prüfung).
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_BITV_TEST_ID = "BITV_9_1_4_2_TON_ABSCHALTBAR"


async def check_ton_abschaltbar(ctx: CheckContext):
    """BITV 9.1.4.2 — Audio/Video mit autoplay ohne muted (Ton nicht abschaltbar)."""
    errors = []
    for video in ctx.soup.find_all("video"):
        if is_accessible_element(video) and video.has_attr("autoplay") and not video.has_attr("muted"):
            errors.append(finding(
                _BITV_TEST_ID,
                "Video mit autoplay ohne muted — Ton startet automatisch und "
                "ist nicht über einen Seitenbeginn-Mechanismus abschaltbar",
                get_dom_path(video),
            ))
    for audio in ctx.soup.find_all("audio"):
        if is_accessible_element(audio) and audio.has_attr("autoplay") and not audio.has_attr("muted"):
            errors.append(finding(
                _BITV_TEST_ID,
                "Audio mit autoplay ohne muted — Ton startet automatisch und "
                "ist nicht über einen Seitenbeginn-Mechanismus abschaltbar",
                get_dom_path(audio),
            ))
    return errors
