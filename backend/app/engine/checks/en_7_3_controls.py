"""EN 301 549 7.3 — Player-Steuerung für Untertitel und Audiodeskription.

Fix (Review): "ad" nur als eigenständiges Wort (kein "Adresse"-Substring-Match);
natives controls-Attribut liefert den Untertitel-Button; Audiodeskription
braucht (nur bei Video) eine eigene Steuerung.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_AD_WORD_RE = re.compile(r"\bad\b")

_CAPTION_WORDS = ["untertitel", "caption", "cc", "transkript", "transcript"]
_AD_WORDS = ["audiodeskription", "description"]


def _btn_has_text(btn, words: list[str]) -> bool:
    all_text = f"{btn.get_text() or ''} {btn.get('aria-label') or ''} {btn.get('title') or ''}".lower()
    if any(w in all_text for w in words):
        return True
    # "ad" nur als eigenes Wort matchen, nicht in "Adresse" / "adaptive"
    return bool(_AD_WORD_RE.search(all_text))


async def check_caption_ad_controls(ctx: CheckContext):
    """EN 7.3 — Steuerung für Untertitel/Audiodeskription am Player."""
    errors = []
    for media in ctx.soup.find_all(["video", "audio"]):
        if not is_accessible_element(media):
            continue
        controls_container = media.parent or media
        all_controls = controls_container.find_all(["button", "a"])
        has_caption_btn = any(_btn_has_text(b, _CAPTION_WORDS) for b in all_controls)
        # Natives controls-Attribut: der Browser liefert den Untertitel-Button.
        has_caption_btn = has_caption_btn or media.has_attr("controls")
        if not has_caption_btn:
            errors.append(finding("EN_7_3_CONTROLS",
                                  "Player ohne Steuerung für Untertitel",
                                  get_dom_path(media)))
            continue
        if media.name == "video":
            has_ad_btn = any(_btn_has_text(b, _AD_WORDS) for b in all_controls)
            if not has_ad_btn:
                errors.append(finding("EN_7_3_CONTROLS",
                                      "Player ohne Steuerung für Audiodeskription",
                                      get_dom_path(media)))
    return errors
