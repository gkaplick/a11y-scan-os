"""WCAG 1.3.1 — Info und Beziehungen: Datentabellen mit Header-Zellen.

Fix (Review): nur Datentabellen prüfen (Heuristik: caption/summary, <th> oder
>2 Zeilen mit Text — Layout-Raster bleiben außen vor); `scope` zählt nur auf
<th> (auf <td> ist es nicht zulässig).
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element


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


async def check_table_headers(ctx: CheckContext):
    """WCAG 1.3.1 — Datentabelle ohne <th>-Header-Zellen."""
    errors = []
    for table in ctx.soup.find_all("table"):
        if not is_accessible_element(table):
            continue
        if not _is_data_table(table):
            continue
        if table.find("th") is None:
            errors.append(finding("WCAG_1_3_1_SR_TABLE_HEADERS",
                                  "Datentabelle ohne <th>-Header-Zellen", get_dom_path(table)))
    return errors
