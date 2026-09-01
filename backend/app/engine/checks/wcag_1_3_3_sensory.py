"""WCAG 1.3.3 — Sensorische Merkmale (ohne sensorischen Bezug nutzbar).

Gleiche Regel wie BITV 9.1.3.3 (eine Norm, zwei Systeme): Anweisungen dürfen
sich nicht ausschließlich auf Farbe, Form oder Position beziehen. Erkannt
werden typische Formulierungen:
- Richtung/Position + Bedienelement: „linke Spalte", „oberen Bereich",
- Farbe + Bedienelement: „roter Button", „grüne Taste".

Nur adverbiale/adjektivische Kombinationen mit einem Bedien-/Struktur-Begriff
werden gewertet („links" allein in Prosa ist kein Befund). Reine
Farb-Legenden ohne Handlungsanweisung (z. B. „legende: rot = Pflichtfeld")
bleiben außen vor — dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "WCAG_1_3_3_SENSORY"

_SENSORY = re.compile(
    r"\b(?:linke|linken|rechte|rechten|obere|oberen|untere|unteren)\s+"
    r"(?:Spalte|Seite|Box|Bereich|Menü|Menu|Taste|Button|Schaltfläche|"
    r"Kästchen|Feld|Liste|Rand|Ecke)\b"
    r"|\b(?:rote|roten|rotem|grüne|grünen|grünem|blaue|blauen|blauem|"
    r"gelbe|gelben|weiße|weißen|schwarze|schwarzen)\s+"
    r"(?:Taste|Button|Schaltfläche|Link|Menü|Menu|Feld|Kästchen|Pfeil|Knopf)\b",
    re.IGNORECASE,
)

# Kurze Textfragmente = Anweisungskandidaten; lange Absätze meiden
_TEXT_NODES = ("p", "li", "td", "th", "figcaption", "label", "dt", "dd")


async def check_sensory(ctx: CheckContext):
    """WCAG 1.3.3 — Anweisung nur über sensorische Merkmale (Position/Farbe)."""
    errors = []
    for el in ctx.soup.find_all(_TEXT_NODES):
        if not is_accessible_element(el):
            continue
        text = el.get_text(" ", strip=True)
        if len(text) > 500:
            continue  # langer Prosa-Block, kein Anweisungs-Fragment
        match = _SENSORY.search(text)
        if not match:
            continue
        snip = text[max(0, match.start() - 25):match.end() + 25]
        errors.append(finding(
            _TEST_ID,
            f"Anweisung bezieht sich auf sensorische Merkmale: „…{snip}…“ "
            "(z. B. Position/Farbe) — zusätzlich unabhängig beschreiben",
            get_dom_path(el),
        ))
    return errors[:5]
