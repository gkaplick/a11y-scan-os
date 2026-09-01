"""BITV 9.1.3.1g — Kein Strukturmarkup für Layouttabellen.

WCAG 1.3.1 (Info und Beziehungen): Tabellenstruktur-Markup (th, caption,
summary, scope, headers, abbr) übermittelt Screenreadern Semantik — für
Layouttabellen ist genau das falsch.

Erkannt wird die widersprüchliche Kombination: eine als Layout deklarierte
Tabelle (role="presentation"/role="none") trägt dennoch Strukturmarkup oder
enthält th-Zellen. Eine echte Datentabelle mit th/caption ist kein Befund
(korrektes Strukturmarkup); eine schlichte Layouttabelle ohne Strukturmarkup
ebenfalls nicht (dort greift ggf. 9.1.3.1e/9.1.3.1f).
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_1_3_1g_KEIN_STRUKTURMARKUP_FUER_LAYOUTTABELLEN"

_STRUCTUR_ATTRIBUTE = ("scope", "headers", "abbr")


async def check_kein_strukturmarkup_fuer_layouttabellen(ctx: CheckContext):
    """BITV 9.1.3.1g — Layouttabelle mit Strukturmarkup (Semantik-Widerspruch)."""
    errors = []
    for table in ctx.soup.find_all("table"):
        if not is_accessible_element(table):
            continue
        role = (table.get("role") or "").lower()
        if role not in ("presentation", "none"):
            continue  # keine als Layout deklarierte Tabelle

        probleme: list[str] = []
        if table.find("th"):
            probleme.append("th-Zellen")
        if table.find("caption"):
            probleme.append("<caption>")
        if table.get("summary"):
            probleme.append("summary-Attribut")
        for zelle in table.find_all(["td", "th"]):
            for attr in _STRUCTUR_ATTRIBUTE:
                if zelle.get(attr):
                    probleme.append(f"{attr}-Attribut")
                    break

        if probleme:
            errors.append(finding(
                _TEST_ID,
                f"Layouttabelle (role=\"{role}\") verwendet "
                f"Tabellenstruktur-Markup: {', '.join(dict.fromkeys(probleme))} "
                "— für reines Layout entfernen",
                get_dom_path(table),
            ))
    return errors[:10]
