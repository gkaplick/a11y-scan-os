"""WCAG 2.2.1 — Zeitbegrenzungen: kein automatisches Meta-Refresh.

Fix (Review): content wird geparst. Ausnahmen nach WCAG/Understanding:
0;url=… (Sofort-Redirect) ist keine Zeitbegrenzung; > 20 h Refresh/Redirect
ist praktisch keine Einschränkung.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path

_META_REFRESH_RE = re.compile(
    r"^\s*(\d+)\s*(?:;\s*url\s*=\s*['\"]?([^'\"]*?)['\"]?)?\s*$", re.IGNORECASE
)
_TWENTY_HOURS_S = 20 * 3600


async def check_meta_refresh(ctx: CheckContext):
    """WCAG 2.2.1 — Meta-Refresh mit relevanter Zeitbegrenzung."""
    errors = []
    for tag in ctx.soup.find_all("meta", attrs={"http-equiv": "refresh"}):
        content = (tag.get("content") or "").strip()
        m = _META_REFRESH_RE.match(content)
        if not m:
            errors.append(finding("WCAG_2_2_1_META_REFRESH",
                                  f"Meta-Refresh mit unparsebarem content='{content}'",
                                  get_dom_path(tag)))
            continue
        seconds = int(m.group(1))
        url = m.group(2)
        if seconds == 0 and url:
            continue  # Sofort-Redirect (0;url=...) ist keine Zeitbegrenzung
        if seconds > _TWENTY_HOURS_S:
            continue  # > 20 h → praktisch keine Einschränkung
        errors.append(finding("WCAG_2_2_1_META_REFRESH",
                              "Meta-Refresh: Weiterleitung/Neuladen nach "
                              f"{seconds}s" + (f" zu '{url}'" if url else ""),
                              get_dom_path(tag)))
    return errors
