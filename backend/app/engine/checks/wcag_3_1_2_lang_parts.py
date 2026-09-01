"""WCAG 3.1.2 — Sprache einzelner Textpassagen: deklarierte Wechsel auswertbar.

Fix (Review): nicht nur leere lang-Attribute melden — ein Element-`lang` gleich
Seiten-`lang` ist kein Wechsel (kein Befund), eine unauswertbare Angabe
(leer/kein BCP-47, z. B. lang="englisch") bei einem Wechsel ist ein Befund.
Ungemarkte Wechsel erfordern Sprachdetektion und sind hier nicht geprüft.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path

_BCP47_RE = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")


async def check_lang_parts(ctx: CheckContext):
    """WCAG 3.1.2 — Sprachwechsel mit nicht auswertbarer Sprachangabe."""
    root = ctx.soup
    html_tag = root.find("html")
    page_lang = (html_tag.get("lang") or "").strip() if html_tag else ""
    errors = []
    for elem in root.find_all(attrs={"lang": True}):
        if elem.name == "html":
            continue
        lang = (elem.get("lang") or "").strip()
        if lang == page_lang:
            continue  # kein Wechsel deklariert
        if not lang or not _BCP47_RE.match(lang):
            errors.append(finding("WCAG_3_1_2_LANG_PARTS",
                                  f"Nicht auswertbare Sprachangabe bei Wechsel: '{lang}'",
                                  get_dom_path(elem)))
    return errors
