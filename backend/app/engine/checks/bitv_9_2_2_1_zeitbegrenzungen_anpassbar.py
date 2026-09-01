"""BITV_9_2_2_1_ZEITBEGRENZUNGEN_ANPASSBAR — Zeitbegrenzungen anpassbar.

Quelle: docs/bitvtest/9.2.2.1.json (WCAG 2.2.1, Level A).

Der Prüfschritt verlangt (Abschnitt 2.1): Taucht http-equiv="refresh" im
Kopfbereich auf, muss content="0" sein — also eine Sofort-Weiterleitung ohne
Zeitverzögerung. Periodisches Neuladen und zeitverzögerte Weiterleitungen
sind Verstöße. Die Abschalt-/Verlängerbarkeit von Session-Zeitbegrenzungen
(Abschnitt 2.2) ist serverseitig und nicht aus dem Quelltext ableitbar —
das bleibt manuell zu bewerten.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path

_TEST_ID = "BITV_9_2_2_1_ZEITBEGRENZUNGEN_ANPASSBAR"

_META_REFRESH_RE = re.compile(
    r"^\s*(\d+)\s*(?:;\s*url\s*=\s*['\"]?([^'\"]*?)['\"]?)?\s*$", re.IGNORECASE
)
_TWENTY_HOURS_S = 20 * 3600


async def check_zeitbegrenzungen_anpassbar(ctx: CheckContext):
    """BITV_9_2_2_1 — Meta-Refresh mit relevanter Zeitbegrenzung."""
    errors = []
    for tag in ctx.soup.find_all("meta", attrs={"http-equiv": "refresh"}):
        content = (tag.get("content") or "").strip()
        m = _META_REFRESH_RE.match(content)
        if not m:
            errors.append(finding(
                _TEST_ID,
                f"Meta-Refresh mit unparsebarem content='{content}' — "
                "Zeitbegrenzung nicht anpassbar",
                get_dom_path(tag),
            ))
            continue
        seconds = int(m.group(1))
        url = m.group(2)
        if seconds == 0 and url:
            continue  # Sofort-Redirect (0;url=...) ist keine Zeitbegrenzung
        if seconds > _TWENTY_HOURS_S:
            continue  # > 20 h → praktisch keine Einschränkung
        errors.append(finding(
            _TEST_ID,
            "Meta-Refresh: Weiterleitung/Neuladen nach "
            f"{seconds}s" + (f" zu '{url}'" if url else "") +
            " — Zeitbegrenzung ist nicht abschaltbar/verlängerbar",
            get_dom_path(tag),
        ))
    return errors
