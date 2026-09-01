"""WCAG 2.4.4 — Linkzweck (aus Text oder programmatischem Kontext).

Fixes (Review): der Link-Name wird per AccName-Heuristik aufgelöst
(aria-labelledby-Referenz löst sich auf → kein FP); generische Linktexte
("hier", "mehr", "read more", "click here") gelten als nicht beschreibend.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import resolve_accessible_name

# Nur exakte, nicht-beschreibende Kurztexte (kein Substring-Match).
_GENERIC_LINKS = {
    "hier", "hier klicken", "klicken sie hier",
    "mehr", "weiter", "weiterlesen", "weiter lesen", "mehr lesen",
    "read more", "click here", "more", "learn more",
}


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


async def check_link_purpose(ctx: CheckContext):
    """WCAG 2.4.4 — Link ohne beschreibenden Namen (fehlend oder generisch)."""
    errors = []
    root = ctx.soup
    for link in ctx.soup.find_all("a", href=True):
        if not is_accessible_element(link):
            continue
        name = resolve_accessible_name(link, root).strip()
        if not name:
            errors.append(finding("WCAG_2_4_4_LINK_TEXT",
                                  f"href='{link.get('href', 'N/A')}' (ohne Text)",
                                  get_dom_path(link)))
            continue
        if _normalize(name) in _GENERIC_LINKS:
            errors.append(finding("WCAG_2_4_4_LINK_TEXT",
                                  f"href='{link.get('href', 'N/A')}' "
                                  f"(generischer Linktext: '{name}')",
                                  get_dom_path(link)))
    return errors
