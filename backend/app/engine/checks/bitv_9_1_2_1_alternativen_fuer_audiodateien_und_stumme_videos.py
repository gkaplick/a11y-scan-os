"""BITV 9.1.2.1 — Alternativen für Audiodateien und stumme Videos.

Reine Audio-Inhalte und als stumm markierte Videos (``muted``) brauchen eine
Medienalternative (Transkript/Volltext) in unmittelbarer Nähe oder einen
aussagekräftigen Link darauf. Tonbehaftete Videos fallen unter 9.1.2.2
(Untertitel) und 9.1.2.3 (Audiodeskription/Volltext).

Die Alternative darf nicht selbst wieder audio-visuell sein — ein zweites
<audio>-Element ist keine Medienalternative. Erkannt werden verlinkte
Transkripte/Untertitel im selben Block und aria-describedby-Referenzen
(geteilter Algorithmus ``_media_has_transcript``).
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import _media_has_transcript

_TEST_ID = "BITV_9_1_2_1_ALTERNATIVEN_FUER_AUDIODATEIEN_UND_STUMME_VIDEOS"


async def check_alternativen_fuer_audiodateien_und_stumme_videos(ctx: CheckContext):
    """BITV 9.1.2.1 — Audio/stumme Videos ohne Transkript oder Medienalternative."""
    errors = []
    for media in ctx.soup.find_all(["audio", "video"]):
        if not is_accessible_element(media):
            continue
        # Tonbehaftete Videos sind nicht dieser Prüfschritt (9.1.2.2/9.1.2.3).
        if media.name == "video" and media.get("muted") is None:
            continue
        if _media_has_transcript(media, ctx.soup):
            continue
        errors.append(finding(
            _TEST_ID,
            f"<{media.name}> ohne Transkript oder Medienalternative",
            get_dom_path(media),
        ))
    return errors
