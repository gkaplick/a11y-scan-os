"""WCAG 4.1.2 — Name, Rolle, Wert: interaktive Elemente mit zugänglichem Namen.

Fixes (Review): zugänglicher Name über die AccName-Heuristik (_helpers),
d. h. verwaiste aria-labelledby-Referenzen zählen nicht als Name; <button>
wird hier übersprungen (eigener Check WCAG_4_1_2_BUTTON_NAME), um Doppel-
befunde zu vermeiden.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import has_accessible_name

_INTERACTIVE_ROLE_RE = re.compile(r"button|link|textbox|combobox|checkbox|radio|slider|spinbutton")


async def check_aria_label_missing(ctx: CheckContext):
    """WCAG 4.1.2 — interaktives Element ohne zugänglichen Namen."""
    root = ctx.soup
    interactive = root.find_all(["input", "select", "textarea", "a"])
    interactive += root.find_all(attrs={"role": _INTERACTIVE_ROLE_RE})
    errors = []

    for elem in interactive:
        if not is_accessible_element(elem):
            continue
        if elem.name == "button":
            continue  # eigener Check: WCAG_4_1_2_BUTTON_NAME
        if (elem.get("type") or "").lower() == "hidden":
            continue
        if elem.get("inert") is not None:
            continue
        if re.search(r"display\s*:\s*none|visibility\s*:\s*hidden",
                     elem.get("style") or "", re.I):
            continue
        if has_accessible_name(elem, root):
            continue
        info = elem.name
        if elem.get("type"):
            info += f"[type={elem.get('type')}]"
        if elem.get("id"):
            info += f"#{elem.get('id')}"
        elif elem.get("class"):
            cls = elem.get("class")
            info += f".{cls[0] if isinstance(cls, list) else cls}"
        errors.append(finding("WCAG_4_1_2_ARIA_LABEL_MISSING", f"<{info}> ohne Beschriftung",
                              get_dom_path(elem)))
    return errors
