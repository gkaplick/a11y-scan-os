"""BITV_9_1_2_2_AUFGEZEICHNETE_VIDEOS_MIT_UNTERTITELN — Aufgezeichnete Videos mit Untertiteln.

Der BITV-Prüfschritt 9.1.2.2
wertet als Zwischenstufe (\"Teilweise erfüllt\") eine vollständige
Textalternative (Transkript) in unmittelbarer Nähe des Videos oder über einen
klar bezeichneten Link als ausreichend. Videos mit einer solchen
Textalternative werden daher nicht als Befund gemeldet. Nur kind=\"captions\"
ist eine Untertitel-Alternative — kind=\"subtitles\" ist eine Übersetzung ohne
Geräusche-Information; ein <track> ohne src liefert keine Untertitel.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding, get_dom_path
from ._helpers import (
    _media_elements,
    _media_has_captions,
    _media_ist_design_element,
    resolve_idrefs,
)

_BITV_TEST_ID = "BITV_9_1_2_2_AUFGEZEICHNETE_VIDEOS_MIT_UNTERTITELN"

# Signalwörter für eine verlinkte/benachbarte Textalternative (Transkript)
_TRANSKRIPT_KEYWORDS = (
    "transkript", "transcript", "textfassung", "textversion", "text-version",
    "volltext", "wortlaut", "mitschrift", "abschrift",
)


def _hat_textalternative(video, root) -> bool:
    """Erkennt eine Transkript-/Textalternative in der Nähe des Videos.

    Quellen: aria-describedby am Video sowie Links im engeren Container (Video
    selbst, Eltern-/Großeltern-Ebene, figure/figcaption), deren Text oder href
    ein Transkript-Signalwort enthält.
    """
    describedby = video.get("aria-describedby")
    if describedby and resolve_idrefs(root, describedby).strip():
        return True

    scope = video
    for _ in range(3):
        for a in scope.find_all("a"):
            label = f"{a.get_text(' ', strip=True)} {a.get('href') or ''}".lower()
            if any(k in label for k in _TRANSKRIPT_KEYWORDS):
                return True
        if scope.parent is None:
            break
        scope = scope.parent
    return False


async def check_aufgezeichnete_videos_mit_untertiteln(ctx: CheckContext) -> list[Finding]:
    """BITV 9.1.2.2 — Video ohne Untertitel-Spur (kind=\"captions\") und ohne Textalternative."""
    errors = []
    root = ctx.soup
    for video in _media_elements(ctx, kinds=("video",)):
        # Reines Gestaltungselement (stumm, ohne Bedienelemente) hat keinen
        # gesprochenen Inhalt, für den Untertitel nötig wären.
        if _media_ist_design_element(video):
            continue
        if _media_has_captions(video):
            continue
        if _hat_textalternative(video, root):
            continue
        errors.append(finding(
            _BITV_TEST_ID,
            "Aufgezeichnetes Video ohne Untertitel-Spur und ohne erkennbare Textalternative",
            get_dom_path(video),
        ))
    return errors
