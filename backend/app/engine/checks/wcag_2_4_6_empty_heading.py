"""WCAG 2.4.6 — Überschriften beschreiben den Inhalt: nicht leer.

Fix (Review): Ein img[alt] innerhalb der Überschrift zählt als Text —
get_text() liefert alt-Attribute nicht mit. Auch ein aria-label ist ein
zugänglicher Name.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path
from ._helpers import _collect_headings


async def check_empty_heading(ctx: CheckContext):
    """WCAG 2.4.6 — Überschrift ohne zugänglichen Namen (Text/img[alt]/aria-label)."""
    errors = []
    for tag in _collect_headings(ctx):
        text = tag.get_text(" ", strip=True)
        img_alts = [a.strip() for img in tag.find_all("img") if (a := (img.get("alt") or "").strip())]
        aria_label = (tag.get("aria-label") or "").strip()
        if not text and not img_alts and not aria_label:
            errors.append(finding("WCAG_2_4_6_EMPTY_HEADING",
                                  f"<{tag.name}> ohne Text", get_dom_path(tag)))
    return errors
