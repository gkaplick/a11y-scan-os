"""WCAG 2.4.1 — Mechanismen zum Überbrücken wiederkehrender Blöcke.

Fix (Review): Landmarken sind laut Understanding 2.4.1 (ARIA11/H69) ein
ausreichender Mechanismus — <main>/role="main" zählt. Skip-Link-Keywords
präzisiert (deutsch); das Sprungziel muss existieren.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding

_SKIP_KEYWORDS = [
    "skip to content", "skip to main", "skip navigation", "skip",
    "zum hauptinhalt", "zum inhalt", "zum seiteninhalt", "direkt zum inhalt",
    "springe zum inhalt", "hauptinhalt",
]


async def check_skip_links(ctx: CheckContext):
    """WCAG 2.4.1 — kein Mechanismus (Landmarke/Skip-Link) zum Hauptinhalt."""
    root = ctx.soup
    if root.find("main") or root.find(attrs={"role": "main"}):
        return []  # Landmarke ist ein ausreichender Bypass-Mechanismus
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
                return []  # Skip-Link mit existierendem Ziel
            # Sprungziel fehlt → weiter nach einem funktionierenden Mechanismus suchen
    return [finding("WCAG_2_4_1_SKIP_LINKS", "Kein Skip-Link zum Hauptinhalt gefunden", "body")]
