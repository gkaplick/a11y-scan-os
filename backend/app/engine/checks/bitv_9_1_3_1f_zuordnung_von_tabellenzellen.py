"""BITV_9_1_3_1f_ZUORDNUNG_VON_TABELLENZELLEN — Zuordnung von Tabellenzellen.

Prüfschritt 9.1.3.1f verlangt die Vollständigkeit und formale Korrektheit der
Zuordnung von Tabelleninhalten zu ihren Überschriften:

- In komplexen Datentabellen (mehrstufige Zeilen-/Spaltenüberschriften) muss der
  Bezug von Überschriften und Inhalten über ``scope`` oder über ``id``/``headers``
  ausdrücklich definiert sein.
- Ausdrückliche ``headers``/``id``-Zuordnungen (auch in einfachen Datentabellen,
  wo sie eigentlich nicht nötig wären) müssen korrekt sein — jede
  ``headers``-Referenz muss auf eine Zelle derselben Tabelle verweisen
  (WCAG-Failure F90).
- ``scope`` ist nur auf ``th`` zulässig und darf nur die Werte ``row``,
  ``col``, ``rowgroup`` oder ``colgroup`` tragen; auf ``td`` ist es eine
  fehlerhafte Zuordnung.

Grundlage ist der Aufbau der Datentabelle (Prüfschritt 9.1.3.1e); dieser Check
beschränkt sich auf die Zuordnung der Inhalte zu den Überschriften.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element


def _is_data_table(table) -> bool:
    """Datentabellen-Heuristik (Layout-Raster ausschließen).

    Identisch zur Heuristik des abdeckenden WCAG-Checks 1.3.1: eine Tabelle mit
    ``caption``/``summary``, mit ``th``-Zellen oder mit mehr als zwei Zeilen und
    Textinhalt gilt als Datentabelle.
    """
    if table.find("caption") is not None or (table.get("summary") or "").strip():
        return True
    if table.find("th") is not None:
        return True
    rows = table.find_all("tr")
    if len(rows) <= 2:
        return False
    return any(cell.get_text(strip=True)
               for row in rows for cell in row.find_all(["td", "th"], recursive=False))


def _table_cells(table) -> list:
    """Zellen dieser Tabelle (verschachtelte Tabellen bleiben außen vor)."""
    return [cell for cell in table.find_all(["td", "th"])
            if cell.find_parent("table") is table]


def _cell_ids(table) -> set[str]:
    """Alle ``id``-Angaben der Zellen einer Tabelle."""
    return {cid for cell in _table_cells(table)
            if (cid := (cell.get("id") or "").strip())}


def _table_rows(table) -> list:
    """Zeilen dieser Tabelle (verschachtelte Tabellen bleiben außen vor)."""
    return [row for row in table.find_all("tr")
            if row.find_parent("table") is table]


def _has_multi_level_headers(table) -> bool:
    """Heuristik für mehrstufige Zeilen-/Spaltenüberschriften (komplexe Tabelle).

    Komplex im Sinne des Prüfschritts ist eine Datentabelle, wenn
    - eine Header-Zelle über ``rowspan``/``colspan`` > 1 mehrere Ebenen abdeckt
      oder
    - mehrere aufeinanderfolgende Kopfzeilen am Tabellenanfang stehen
      (gruppierte Spaltenüberschriften, z. B. Jahreszeiten über Monaten).

    Eine reine Kopfspalte (``th`` in der ersten Spalte jeder Datenzeile) macht
    eine Tabelle dagegen nicht komplex — dort genügen ``th``/``td`` (H63).
    """
    for th in table.find_all("th"):
        if th.find_parent("table") is not table:
            continue
        if int(th.get("rowspan") or 1) > 1 or int(th.get("colspan") or 1) > 1:
            return True
    header_rows = 0
    for row in _table_rows(table):
        cells = row.find_all(["td", "th"], recursive=False)
        if not cells:
            continue
        if all(cell.name == "th" for cell in cells):
            header_rows += 1
        else:
            break
    return header_rows > 1


def _has_explicit_association(table) -> bool:
    """Irgendeine Zelle dieser Tabelle nutzt ``headers`` oder ``scope``."""
    for cell in _table_cells(table):
        if cell.get("headers"):
            return True
        if cell.name == "th" and cell.get("scope"):
            return True
    return False


async def check_zuordnung_von_tabellenzellen(ctx: CheckContext):
    """BITV_9_1_3_1f_ZUORDNUNG_VON_TABELLENZELLEN — Zuordnung von Tabellenzellen."""
    errors = []
    for table in ctx.soup.find_all("table"):
        if not is_accessible_element(table):
            continue
        if not _is_data_table(table):
            continue
        ids = _cell_ids(table)

        # 1. headers/id-Zuordnungen müssen auf Zellen derselben Tabelle verweisen
        for cell in _table_cells(table):
            headers = (cell.get("headers") or "").strip()
            if not headers:
                continue
            for ref in headers.split():
                if ref not in ids:
                    errors.append(finding(
                        "BITV_9_1_3_1f_ZUORDNUNG_VON_TABELLENZELLEN",
                        f"headers-Referenz '{ref}' verweist auf keine Zelle innerhalb der Tabelle",
                        get_dom_path(cell),
                    ))

        # 2. scope nur auf th und nur mit gültigem Wert
        for td in table.find_all("td"):
            if td.find_parent("table") is not table:
                continue
            if td.get("scope"):
                errors.append(finding(
                    "BITV_9_1_3_1f_ZUORDNUNG_VON_TABELLENZELLEN",
                    "scope-Attribut auf <td> unzulässig — nur auf <th> erlaubt",
                    get_dom_path(td),
                ))
        for th in table.find_all("th"):
            if th.find_parent("table") is not table:
                continue
            scope = (th.get("scope") or "").strip().lower()
            if scope and scope not in ("row", "col", "rowgroup", "colgroup"):
                errors.append(finding(
                    "BITV_9_1_3_1f_ZUORDNUNG_VON_TABELLENZELLEN",
                    f"Ungültiger scope-Wert '{scope}' auf <th> — erlaubt: row, col, rowgroup, colgroup",
                    get_dom_path(th),
                ))

        # 3. Komplexe Datentabellen brauchen eine ausdrückliche Zuordnung
        if _has_multi_level_headers(table) and not _has_explicit_association(table):
            errors.append(finding(
                "BITV_9_1_3_1f_ZUORDNUNG_VON_TABELLENZELLEN",
                "Komplexe Datentabelle ohne explizite Zuordnung (scope oder headers/id)",
                get_dom_path(table),
            ))
    return errors
