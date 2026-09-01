"""WCAG 2.4.1 — Iframes ohne beschreibendes title-Attribut."""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element


async def check_iframe_title(ctx: CheckContext):
    """WCAG 2.4.1 — iframe ohne beschreibendes title-Attribut."""
    errors = []
    for iframe in ctx.soup.find_all("iframe"):
        if is_accessible_element(iframe) and not iframe.get("title", "").strip():
            errors.append(finding("WCAG_2_4_1_IFRAME_TITLE",
                                  f"src='{iframe.get('src', 'N/A')}'", get_dom_path(iframe)))
    return errors
