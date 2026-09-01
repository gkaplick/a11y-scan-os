"""WCAG 1.3.1 — Überschriftenebenen überspringen keine Stufen.

Die geteilte Überschriften-Sammlung (_collect_headings) filtert bereits
aria-hidden-Teilbäume.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path
from ._helpers import _collect_headings


async def check_heading_skip(ctx: CheckContext):
    """WCAG 1.3.1 — Überschriftenebenen springen (z. B. h2 → h4)."""
    errors = []
    headings = _collect_headings(ctx)
    prev_level = None
    for u in headings:
        current_level = int(u.name[1])
        if prev_level is not None and current_level > prev_level + 1:
            errors.append(finding("WCAG_1_3_1_HEADING_SKIP",
                                  f"Überschriften-Sprung von h{prev_level} zu h{current_level}",
                                  get_dom_path(u)))
        prev_level = current_level
    return errors
