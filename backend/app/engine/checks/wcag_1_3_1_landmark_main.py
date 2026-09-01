"""WCAG 1.3.1 — Info und Beziehungen: genau ein main-Landmark.

Fixes (Review): <main role="main"> zählt nur einmal (Element-Identity-Dedupe,
sonst Doppelbefund); per CSS display:none ausgeblendete Mains sind nicht
sichtbar.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path


async def check_landmark_main(ctx: CheckContext):
    """WCAG 1.3.1 — mehr als ein sichtbares main-Landmark."""
    root = ctx.soup
    mains = root.find_all(attrs={"role": "main"}) + root.find_all("main")
    unique = []
    seen = set()
    for el in mains:
        if id(el) not in seen:
            seen.add(id(el))
            unique.append(el)
    visible_mains = [
        el for el in unique
        if el.get("hidden") is None
        and el.get("aria-hidden", "").lower() != "true"
        and el.get("inert") is None
        and not re.search(r"display\s*:\s*none", el.get("style") or "", re.I)
    ]
    errors = []
    for el in visible_mains[1:]:
        errors.append(finding("WCAG_1_3_1_LANDMARK_MAIN",
                              "Mehr als ein sichtbares main-Landmark — genau eines erwartet",
                              get_dom_path(el)))
    return errors
