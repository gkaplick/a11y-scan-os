"""BITV 9.2.5.3 — Sichtbare Beschriftung Teil des zugänglichen Namens.

Die sichtbare Beschriftung eines Bedienelements muss im zugänglichen Namen
enthalten sein (WCAG 2.5.3, Failure F96). Erkennt Override-Fälle, in denen
eine aria-label-/aria-labelledby-/title-Beschriftung den sichtbaren Text
übersteuert, ohne ihn zu enthalten.

Nur Elemente mit sichtbarem, buchstabenhaltigem Beschriftungstext sind
prüfbar: Icon-/Symbol-Buttons (×, →, ⋮) sind keine Beschriftungen — dort
ist ein aria-label-Override korrekt und wird nicht gemeldet. Der Check prüft
das Statik-DOM (sichtbarer Text ≈ Tag-Text); textuelle <label>-Beschriftungen
werden für Formularfelder ausgewertet.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element
from ._helpers import resolve_accessible_name, visible_label

_TEST_ID = "BITV_9_2_5_3_SICHTBARE_BESCHRIFTUNG_TEIL_DES_ZUGAENGLICHEN_NAMENS"


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def _visible_beschriftung(el, root) -> str:
    """Sichtbare Beschriftung eines Bedienelements — '' wenn keine."""
    if el.name in ("button", "a"):
        return el.get_text(strip=True)
    if el.name == "input" and (el.get("type") or "text").lower() in ("submit", "button", "reset"):
        return (el.get("value") or "").strip()
    if el.name in ("input", "select", "textarea"):
        return visible_label(el, root)
    return el.get_text(strip=True)


def _ist_beschriftungstext(s: str) -> bool:
    """Nur Text mit mindestens einem Buchstaben ist eine „Beschriftung".

    Einzelne Symbol-/Icon-Zeichen (×, →, …) sind keine Labels — ihr
    aria-label-Override ist kein F96-Verstoß.
    """
    return any(c.isalpha() for c in s)


async def check_sichtbare_beschriftung_teil_des_zugaenglichen_namens(ctx: CheckContext):
    """BITV 9.2.5.3 — Sichtbare Beschriftung fehlt im zugänglichen Namen."""
    errors = []
    for el in ctx.soup.find_all(True):
        if not is_accessible_element(el):
            continue
        if el.name in ("a", "button", "input", "select", "textarea"):
            if el.name == "a" and not el.get("href"):
                continue
        elif (el.get("role") or "") not in ("button", "link"):
            continue

        name = resolve_accessible_name(el, ctx.soup)
        sichtbar = _visible_beschriftung(el, ctx.soup)
        if not sichtbar or not _ist_beschriftungstext(sichtbar):
            continue
        if not name:
            continue
        if _normalize(sichtbar) in _normalize(name):
            continue
        # Nur Override-Fälle melden: Ohne aria-/title-Override ist der Name
        # der sichtbare Text selbst (resolve_accessible_name fällt auf ihn
        # zurück) → kein Verstoß.
        if not (el.get("aria-label") or el.get("aria-labelledby") or el.get("title")):
            continue
        errors.append(finding(
            _TEST_ID,
            f"Sichtbare Beschriftung „{sichtbar}“ fehlt im zugänglichen Namen „{name}“",
            get_dom_path(el),
        ))
    return errors
