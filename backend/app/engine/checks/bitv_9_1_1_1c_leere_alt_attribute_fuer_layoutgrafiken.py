"""BITV_9_1_1_1c_LEERE_ALT_ATTRIBUTE_FUER_LAYOUTGRAFIKEN — Leere alt-Attribute für Layoutgrafiken.

Prüfschritt 9.1.1.1c (bitvtest.de): Grafiken ohne informative Funktion
(Layout-/Dekorgrafiken wie Abstandshalter, Farbflächen, Muster, dekorative
Fotos) sollen mit leerem ``alt=""`` ausgezeichnet werden. Bei solchen Grafiken
muss auch ein ``title``-Attribut fehlen oder leer sein (H67). Dekorative Icon
Fonts und Inline-SVGs sollen mit ``aria-hidden="true"`` vor assistiven
Techniken versteckt werden.

Automatisierbar:
- ``<img>`` ohne ``alt``-Attribut (F38) — dekorative Grafik nicht deklariert
- ``<img>`` mit Füll-Text wie "spacer"/"Abstandshalter"/"leer" als ``alt`` (F39)
- ``<img alt="">`` mit nicht-leerem ``title`` (H67)
- dekoratives Inline-``<svg>`` ohne ``aria-hidden`` und ohne zugänglichen Namen
Nicht automatisierbar: die fachliche Bewertung, ob eine Grafik dekorativ ODER
informativ ist (Abgrenzung zu 9.1.1.1b) sowie die Erkennung von Icon Fonts,
die per CSS ``content`` eingebunden werden (manuelle Prüfung mit den Web
Developer Tools).
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

# Füll-Alt-Texte, die eine Layoutgrafik als solche verraten (F39: Textalternative
# ist nicht null, obwohl die Grafik von AT ignoriert werden soll).
_PLACEHOLDER_ALT_TEXTE = {
    "spacer", "abstand", "abstandhalter", "abstandshalter", "leer", "leerbild",
    "platzhalter", "placeholder", "transparent", "pixel", "blank", "image",
    "grafik", "bild", "deko", "dekorativ", "design-element",
}

_BITV_TEST_ID = "BITV_9_1_1_1c_LEERE_ALT_ATTRIBUTE_FUER_LAYOUTGRAFIKEN"


async def check_leere_alt_attribute_fuer_layoutgrafiken(ctx: CheckContext):
    """BITV 9.1.1.1c — Layoutgrafiken ohne leeres alt-Attribut / unversteckte Deko-SVGs."""
    errors = []
    root = ctx.soup

    # --- <img>-Elemente -----------------------------------------------------
    for img in root.find_all("img"):
        if not is_accessible_element(img):
            continue
        if (img.get("role") or "").lower() in ("presentation", "none"):
            continue  # deklarativ dekorativ → kein alt nötig

        src = img.get("src", "N/A")
        alt = img.get("alt")
        if alt is None:
            # F38: fehlendes alt-Attribut — für eine Layoutgrafik nicht als
            # dekorativ deklariert (Screenreader liest sonst den Dateinamen vor).
            errors.append(finding(
                _BITV_TEST_ID,
                f"Layoutgrafik ohne alt-Attribut (src='{src}')",
                get_dom_path(img),
            ))
            continue

        alt_text = (alt or "").strip()
        if alt_text == "":
            # H67: Bei Grafiken, die AT ignorieren sollen, muss title fehlen/leer sein.
            title = (img.get("title") or "").strip()
            if title:
                errors.append(finding(
                    _BITV_TEST_ID,
                    f"Layoutgrafik mit alt=\"\" hat ein nicht-leeres title-Attribut "
                    f"('{title}') — title muss fehlen oder leer sein (H67)",
                    get_dom_path(img),
                ))
        elif alt_text.lower() in _PLACEHOLDER_ALT_TEXTE:
            # F39: Platzhalter-Text statt leerem alt — stört Screenreader-Nutzende.
            errors.append(finding(
                _BITV_TEST_ID,
                f"Layoutgrafik mit Füll-Alt-Text '{alt_text}' — für dekorative "
                f"Grafiken ist alt=\"\" erforderlich",
                get_dom_path(img),
            ))

    # --- Inline-SVGs --------------------------------------------------------
    # Dekorative SVGs sollen mit aria-hidden="true" versteckt werden. Ein SVG
    # ohne zugänglichen Namen (aria-label/aria-labelledby/<title>/<desc>) und
    # ohne Textinhalt vermittelt nichts — ist es nicht versteckt, wird es von AT
    # als bedeutungslose "image"-Rolle angesagt.
    for svg in root.find_all("svg"):
        if not is_accessible_element(svg):
            continue
        # Symbol-Definitionen/Sprites liegen üblicherweise in per CSS
        # ausgeblendeten SVGs — kein Befund für nicht gerenderte Grafiken.
        if re.search(r"display\s*:\s*none", svg.get("style") or "", re.I):
            continue
        if (svg.get("role") or "").lower() in ("presentation", "none", "img"):
            continue
        hat_namen = bool(
            (svg.get("aria-label") or "").strip()
            or (svg.get("aria-labelledby") or "").strip()
            or svg.find("title")
            or svg.find("desc")
        )
        hat_text = bool(svg.get_text(strip=True))
        if not hat_namen and not hat_text:
            errors.append(finding(
                _BITV_TEST_ID,
                "Dekoratives Inline-SVG ohne zugänglichen Namen ist nicht mit "
                "aria-hidden=\"true\" versteckt",
                get_dom_path(svg),
            ))

    return errors
