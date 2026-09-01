"""BITV_9_2_4_6_AUSSAGEKRAEFTIGE_UEBERSCHRIFTEN_UND_BESCHRIFTUNGEN — Aussagekräftige Überschriften und Beschriftungen.

Quelle: docs/bitvtest/9.2.4.6.json (WCAG 2.4.6, Level A).

Automatisiert prüfbar ist, dass eine Überschrift einen zugänglichen Namen
(Text, img[alt] oder aria-label) besitzt — eine leere Überschrift kann nicht
aussagekräftig sein. Die eigentliche Aussagekraft von Überschriften und
Beschriftungen im Kontext (auch die Korrektheit hinterlegter aria-label) ist
redaktionell und manuell zu bewerten; die reine programmatische
Ermittelbarkeit von Beschriftungen gehört zu 9.1.3.1h.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path
from ._helpers import _collect_headings

_TEST_ID = "BITV_9_2_4_6_AUSSAGEKRAEFTIGE_UEBERSCHRIFTEN_UND_BESCHRIFTUNGEN"


async def check_aussagekraeftige_ueberschriften_und_beschriftungen(ctx: CheckContext):
    """BITV_9_2_4_6 — Überschrift ohne zugänglichen Namen (nicht aussagekräftig)."""
    errors = []
    for tag in _collect_headings(ctx):
        text = tag.get_text(" ", strip=True)
        img_alts = [a.strip() for img in tag.find_all("img")
                    if (a := (img.get("alt") or "").strip())]
        aria_label = (tag.get("aria-label") or "").strip()
        if not text and not img_alts and not aria_label:
            errors.append(finding(
                _TEST_ID,
                f"<{tag.name}> ohne Text — Überschrift ist nicht aussagekräftig",
                get_dom_path(tag),
            ))
    return errors
