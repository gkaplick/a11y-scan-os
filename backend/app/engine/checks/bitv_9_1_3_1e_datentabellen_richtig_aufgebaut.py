"""BITV_9_1_3_1e_DATENTABELLEN_RICHTIG_AUFGEBAUT — Datentabellen richtig aufgebaut.

Der BITV-Prüfschritt
9.1.3.1e verlangt zusätzlich, dass Inhalte, die sichtbar als Datentabelle
umgesetzt sind, aber kein natives Tabellen-Markup nutzen, korrekt mit den
ARIA-Rollen role=\"table\"/row/columnheader/rowheader ausgezeichnet sind.
Layout-Raster (reine Gestaltungstabellen) bleiben außen vor.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding, get_dom_path, is_accessible_element

_BITV_TEST_ID = "BITV_9_1_3_1e_DATENTABELLEN_RICHTIG_AUFGEBAUT"


def _is_data_table(table) -> bool:
    """Datentabellen-Heuristik (Layout-Raster ausschließen)."""
    if table.find("caption") is not None or (table.get("summary") or "").strip():
        return True
    if table.find("th") is not None:
        return True
    rows = table.find_all("tr")
    if len(rows) <= 2:
        return False
    return any(cell.get_text(strip=True)
               for row in rows for cell in row.find_all(["td", "th"], recursive=False))


async def check_datentabellen_richtig_aufgebaut(ctx: CheckContext) -> list[Finding]:
    """BITV 9.1.3.1e — Datentabelle ohne korrekt ausgezeichnete Überschriften."""
    errors = []
    root = ctx.soup

    # Native Datentabellen: Zeilen-/Spaltenüberschriften müssen mit <th> ausgezeichnet sein.
    for table in root.find_all("table"):
        if not is_accessible_element(table):
            continue
        if not _is_data_table(table):
            continue
        if table.find("th") is None:
            errors.append(finding(
                _BITV_TEST_ID,
                "Datentabelle ohne <th>-Header-Zellen",
                get_dom_path(table),
            ))

    # ARIA-Tabellen: Rolle table/row/columnheader/rowheader muss vollständig sein.
    for el in root.find_all(attrs={"role": "table"}):
        if el.name == "table":
            continue  # natives <table role="table"> — im nativen Zweig geprüft
        if not is_accessible_element(el):
            continue
        rows = el.find_all(attrs={"role": "row"})
        headers = el.find_all(attrs={"role": ["columnheader", "rowheader"]})
        if not rows or not headers:
            errors.append(finding(
                _BITV_TEST_ID,
                "ARIA-Tabelle ohne vollständige Rollen (row/columnheader/rowheader)",
                get_dom_path(el),
            ))

    return errors
