"""BITV 9.3.1.2 — Anderssprachige Wörter und Abschnitte ausgezeichnet.

Deklarierte Sprachwechsel werden ausgewertet — eine leere oder nicht auswertbare
Sprachangabe (kein BCP-47-Tag, z. B. lang="englisch") bei einem Wechsel ist
ein Befund; ein Element-lang gleich Seiten-lang ist kein Wechsel (kein Befund).
Nicht ausgezeichnete Wechsel erfordern Sprachdetektion und bleiben manuell.
"""
from __future__ import annotations

import re

from ._base import CheckContext, Finding, finding, get_dom_path, is_accessible_element

_BCP47_RE = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,8})*$")
_TEST_ID = "BITV_9_3_1_2_ANDERSSPRACHIGE_WOERTER_UND_ABSCHNITTE_AUSGEZEICHNET"


async def check_anderssprachige_woerter_und_abschnitte_ausgezeichnet(ctx: CheckContext) -> list[Finding]:
    """BITV 9.3.1.2 — Sprachwechsel mit nicht auswertbarer Sprachangabe."""
    root = ctx.soup
    html_tag = root.find("html")
    page_lang = (html_tag.get("lang") or "").strip() if html_tag else ""
    errors = []
    for elem in root.find_all(attrs={"lang": True}):
        if elem.name == "html" or not is_accessible_element(elem):
            continue
        lang = (elem.get("lang") or "").strip()
        if lang == page_lang:
            continue  # kein Wechsel deklariert
        if not lang or not _BCP47_RE.match(lang):
            errors.append(finding(
                _TEST_ID,
                f"Nicht auswertbare Sprachangabe bei Wechsel: '{lang}'",
                get_dom_path(elem),
            ))
    return errors
