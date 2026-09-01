"""WCAG 1.3.1 — Info und Beziehungen: leere Listen.

Fix (Review): <dl> (Definitionslisten) einbeziehen — <dt>/<dd> statt <li>.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element


async def check_empty_list(ctx: CheckContext):
    """WCAG 1.3.1 — leere Liste (<ul>/<ol>/<dl> ohne Einträge)."""
    errors = []
    for lst in ctx.soup.find_all(["ul", "ol", "dl"]):
        if not is_accessible_element(lst):
            continue
        if lst.name == "dl":
            entries = lst.find_all(["dt", "dd"], recursive=False)
        else:
            entries = lst.find_all("li", recursive=False)
        if len(entries) == 0:
            errors.append(finding("WCAG_1_3_1_SR_EMPTY_LIST",
                                  "Leere Liste ohne Einträge", get_dom_path(lst)))
    return errors
