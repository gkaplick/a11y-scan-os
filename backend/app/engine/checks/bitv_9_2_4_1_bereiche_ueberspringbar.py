"""BITV 9.2.4.1 — Bereiche überspringbar.

Der BITV-Prüfschritt verlangt, dass die verschiedenen Inhaltsbereiche (z. B.
Navigation und Inhalt) für Nutzende assistiver Technologien überspringbar bzw.
direkt erreichbar sind. Mindestens eine der Voraussetzungen soll erfüllt sein:
- Sprunglinks (zumindest zum Inhalt),
- HTML5-Elemente zur Bereichsauszeichnung (``header``, ``nav``, ``main``,
  ``aside``, ``footer``) oder die entsprechenden WAI-ARIA document landmarks,
- sinnvolle Bereichsüberschriften.

Zusätzlich sollen iframes ihren Bereich über ein ``title``-Attribut benennen
und mehrfach verwendete Navigations-Landmarken über ``aria-label``/
``aria-labelledby`` unterscheidbar sein.

Der Check kombiniert die drei abdeckenden WCAG-Checks (der Video-Titel-Check
ist eine Teilmenge des allgemeinen iframe-Titel-Checks und wird deshalb nicht
separat geführt) und ergänzt die Prüfung mehrfacher ``nav``-Landmarken.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_SKIP_KEYWORDS = [
    "skip to content", "skip to main", "skip navigation", "skip",
    "zum hauptinhalt", "zum inhalt", "zum seiteninhalt", "direkt zum inhalt",
    "springe zum inhalt", "hauptinhalt",
]


def _has_bypass_mechanism(root) -> bool:
    """True, wenn Sprunglink oder Bereichs-Landmarke vorhanden ist.

    Landmarken sind laut Understanding 2.4.1 (ARIA11/H69) ein ausreichender
    Mechanismus — ``main``/``role="main"`` und ``nav``/``role="navigation"``
    zählen (bitvtest: HTML5-Elemente zur Bereichsauszeichnung).
    """
    if root.find("main") or root.find(attrs={"role": "main"}):
        return True
    if root.find("nav") or root.find(attrs={"role": "navigation"}):
        return True
    skip_links = root.find_all("a", href=re.compile(r"^#"), limit=20)
    for s in skip_links:
        combined = " ".join([
            s.get("href", ""), s.get_text(" ", strip=True),
            " ".join(s.get("class", [])), s.get("title", ""),
            s.get("id", ""), s.get("aria-label", ""),
        ]).lower()
        if any(kw in combined for kw in _SKIP_KEYWORDS):
            target = s.get("href", "#").lstrip("#")
            if target and root.find(id=target):
                return True  # Skip-Link mit existierendem Ziel
            # Sprungziel fehlt → weiter nach einem funktionierenden Mechanismus suchen
    return False


def _navigation_landmarks(root) -> list:
    """Alle nav-/role="navigation"-Elemente (Element-Identity-Dedupe)."""
    seen = set()
    navs = []
    for el in root.find_all(["nav"]) + root.find_all(attrs={"role": "navigation"}):
        if id(el) not in seen:
            seen.add(id(el))
            navs.append(el)
    return navs


async def check_bereiche_ueberspringbar(ctx: CheckContext):
    """BITV 9.2.4.1 — fehlender Bypass-Mechanismus, iframe-Titel, nav-Labels."""
    errors = []
    root = ctx.soup

    # 1) Mechanismus zum Überspringen/Erreichen der Bereiche
    if not _has_bypass_mechanism(root):
        errors.append(finding(
            "BITV_9_2_4_1_BEREICHE_UEBERSPRINGBAR",
            "Kein Mechanismus zum Überspringen wiederkehrender Bereiche "
            "(Sprunglink, main-/nav-Landmarke o. ä.)",
            "body",
        ))

    # 2) iframes mit Inhalten brauchen einen beschreibenden title (H64)
    for iframe in root.find_all("iframe"):
        if is_accessible_element(iframe) and not iframe.get("title", "").strip():
            errors.append(finding(
                "BITV_9_2_4_1_BEREICHE_UEBERSPRINGBAR",
                f"iframe ohne beschreibenden Titel (src='{iframe.get('src', 'N/A')}')",
                get_dom_path(iframe),
            ))

    # 3) Mehrere Navigations-Landmarken sind über aria-label/aria-labelledby
    #    unterscheidbar zu machen (bitvtest: "Teilweise erfüllt oder schlechter")
    navs = _navigation_landmarks(root)
    if len(navs) > 1:
        for el in navs:
            if not is_accessible_element(el):
                continue
            if not (el.get("aria-label") or "").strip() and not (el.get("aria-labelledby") or "").strip():
                errors.append(finding(
                    "BITV_9_2_4_1_BEREICHE_UEBERSPRINGBAR",
                    "Mehrere Navigationsbereiche ohne aria-label/aria-labelledby "
                    "(nicht unterscheidbar, nicht gezielt überspringbar)",
                    get_dom_path(el),
                ))

    return errors
