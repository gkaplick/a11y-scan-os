"""WCAG 2.4.2 — Seite hat einen beschreibenden Titel (<title>)."""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path


async def check_page_title(ctx: CheckContext):
    """WCAG 2.4.2 — <title> fehlt oder leer."""
    root = ctx.soup
    title_tag = root.find("title")
    if not title_tag or not title_tag.get_text(strip=True):
        errors = [finding("WCAG_2_4_2_TITLE", "Fehlendes oder leeres <title>-Tag",
                          get_dom_path(title_tag or getattr(root, "head", None) or root))]
        return errors
    return []
