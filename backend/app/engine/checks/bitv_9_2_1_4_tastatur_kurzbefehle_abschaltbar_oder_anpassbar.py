"""BITV 9.2.1.4 — Tastatur-Kurzbefehle (Einzelzeichen) abschaltbar/anpassbar.

Einzelschritt 1.3 des bitvtest-Prüfschritts: Einzelzeichen-Kurzbefehle sind
nur erlaubt, wenn sie abschaltbar, anpassbar oder an einen Modifikator
(Ctrl/Alt/Meta) gebunden sind.

Der Check erkennt inline-JS-Headler (onkeydown/onkeypress/onkeyup), die ein
einzelnes druckbares Zeichen ohne Modifikator-Abfrage abfangen (z. B.
``onkeydown="if (event.key === 'j') …"`` oder keyCode-Vergleich). Handler
mit ctrlKey/altKey/metaKey-Prüfung gelten als konform. Per
addEventListener registrierte Handler sind aus dem statischen DOM nicht
sichtbar — das ist dokumentierte Grenze der Automatisierung.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_2_1_4_TASTATUR_KURZBEFEHLE_ABSCHALTBAR_ODER_ANPASSBAR"

_HANDLER_ATTRIBUTE = ("onkeydown", "onkeypress", "onkeyup")
# Einzelnes druckbares Zeichen als String-Literal (event.key === 'j').
_SINGLE_CHAR = re.compile(r"""\.key\s*[=!]==?\s*(['"])([^'"\\\s])\1""")
# Numerischer Zeichencode (keyCode/which): druckbare ASCII-Zeichen 32–126.
_KEYCODE = re.compile(r"""\.(?:keyCode|which|charCode)\s*[=!]==?\s*(\d{2,3})""")
_MODIFIER = re.compile(r"""\b(?:ctrlKey|altKey|metaKey)\b""")


def _ist_einzelzeichen(js: str) -> bool:
    if _SINGLE_CHAR.search(js):
        return True
    return any(32 <= int(m.group(1)) <= 126 for m in _KEYCODE.finditer(js))


async def check_tastatur_kurzbefehle_abschaltbar_oder_anpassbar(ctx: CheckContext):
    """BITV 9.2.1.4 — Einzelzeichen-Kurzbefehl ohne Modifikator/Abschaltung."""
    errors = []
    for el in ctx.soup.find_all(True):
        if not is_accessible_element(el):
            continue
        for attr in _HANDLER_ATTRIBUTE:
            js = el.get(attr)
            if not js:
                continue
            if _MODIFIER.search(js):
                continue
            if _ist_einzelzeichen(js):
                errors.append(finding(
                    _TEST_ID,
                    f"Tastatur-Kurzbefehl auf Einzelzeichen in <{el.name}> ohne "
                    "Modifikator, Abschalt- oder Anpassungsmöglichkeit",
                    get_dom_path(el),
                ))
                break
    return errors
