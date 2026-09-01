"""BITV 9.1.3.1d — Inhalt gegliedert.

Prüfschritt 9.1.3.1d fordert, dass Textabsätze mit geeigneten
Strukturelementen ausgezeichnet sind, Zeilenumbrüche nicht über doppelte
``br``-Elemente erzeugt werden und Hervorhebungen mit ``strong``/``em``
ausgezeichnet sind.

Automatisiert prüfbar sind die eindeutigen Fehlermuster des Prüfschritts
(„Nicht voll erfüllt"-Kriterien der bitvtest-Quelle):
- doppelte ``br``-Elemente statt Absatz-Elementen (``p``),
- Leerzeichen-Ketten (``&nbsp;&nbsp;`` …) zur Textformatierung/Spaltenbildung,
- typographische Trennlinien (Reihen von Bindestrichen/Unterstrichen) statt
  eines ``hr``-Elements.

Die qualitative Bewertung der Absatz-Semantik (``p`` vs. ``div``, wobei ``div``
in der Regel akzeptiert wird) sowie die Auszeichnung von Hervorhebungen mit
``strong``/``em`` statt ``b``/``i`` erfordert menschliche Prüfung und bleibt
hier außen vor. Die Strukturelemente für Tabellen, Überschriften, Listen und
Zitate werden in den Prüfschritten 9.1.3.1a–c/e bewertet.
"""
from __future__ import annotations

import re

from bs4 import Comment

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

# Trennlinie aus 3+ typographischen Zeichen (Bindestrich, Unterstrich, Gleich)
_SEPARATOR_LINE_RE = re.compile(r"^\s*[-_=]{3,}\s*$")

# Elemente, deren Textknoten nicht als Inhalt gewertet werden
_SKIP_TEXT_PARENTS = {"script", "style", "pre", "code", "textarea"}


async def check_inhalt_gegliedert(ctx: CheckContext):
    """BITV 9.1.3.1d — doppelte <br>, &nbsp;-Ketten und typographische Trennlinien."""
    errors = []
    root = ctx.soup

    # 1) Doppelte <br>-Elemente als Absatz-Umbruch (2+ aufeinanderfolgende <br>)
    for br in root.find_all("br"):
        if not is_accessible_element(br):
            continue
        # Whitespace-Textknoten zwischen den <br> überspringen
        nxt = br.next_sibling
        while nxt is not None and getattr(nxt, "name", None) is None and not str(nxt).strip():
            nxt = nxt.next_sibling
        if nxt is None or getattr(nxt, "name", None) != "br":
            continue
        # Nur das erste <br> eines Paares melden (das zweite wäre ein Doppelbefund)
        prev = br.previous_sibling
        while prev is not None and getattr(prev, "name", None) is None and not str(prev).strip():
            prev = prev.previous_sibling
        if prev is not None and getattr(prev, "name", None) == "br":
            continue
        errors.append(finding(
            "BITV_9_1_3_1d_INHALT_GEGLIEDERT",
            "Doppelte <br>-Elemente statt Absatz-Element (p) verwendet",
            get_dom_path(br),
        ))

    # 2) &nbsp;-Ketten (2+ aufeinanderfolgende geschützte Leerzeichen) zur Formatierung
    for text_node in root.find_all(string=True):
        if isinstance(text_node, Comment):
            continue
        parent = text_node.parent
        if parent is None or not is_accessible_element(parent):
            continue
        if parent.name in _SKIP_TEXT_PARENTS:
            continue
        if "\xa0\xa0" in text_node:
            errors.append(finding(
                "BITV_9_1_3_1d_INHALT_GEGLIEDERT",
                "Leerzeichen-Kette (&nbsp;&nbsp;…) zur Textformatierung",
                get_dom_path(parent),
            ))

    # 3) Typographische Trennlinien (Reihen von Bindestrichen etc.) statt <hr>
    for text_node in root.find_all(string=True):
        if isinstance(text_node, Comment):
            continue
        parent = text_node.parent
        if parent is None or not is_accessible_element(parent):
            continue
        if parent.name in _SKIP_TEXT_PARENTS:
            continue
        if _SEPARATOR_LINE_RE.match(text_node):
            errors.append(finding(
                "BITV_9_1_3_1d_INHALT_GEGLIEDERT",
                "Trennlinie aus typographischen Zeichen statt <hr>-Element",
                get_dom_path(parent),
            ))

    return errors
