"""BITV 9.2.4.3 — Schlüssige Reihenfolge bei der Tastaturbedienung.

WCAG 2.4.3 (A): Die Fokus-Reihenfolge ist logisch und entspricht der
Reihenfolge, in der Bedeutung vermittelt wird. Ein positives tabindex
(tabindex > 0) hebt ein Element gegen die Dokumentreihenfolge in die
Tab-Reihenfolge (G59-Fail) — die natürliche Reihenfolge wird aufgehoben.

tabindex="0" (natürliche Reihenfolge) und tabindex="-1" (programmatischer
Fokus, z. B. Sprungmarken-Ziel) sind zulässig und kein Befund.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_2_4_3_SCHLUESSIGE_REIHENFOLGE_BEI_DER_TASTATURBEDIENUNG"


async def check_schluessige_reihenfolge_bei_der_tastaturbedienung(ctx: CheckContext):
    """BITV 9.2.4.3 — Elemente mit positivem tabindex brechen die Fokus-Reihenfolge."""
    errors = []
    for el in ctx.soup.find_all(True):
        if not is_accessible_element(el):
            continue
        value = el.get("tabindex")
        if value is None:
            continue
        try:
            if int(value) > 0:
                errors.append(finding(
                    _TEST_ID,
                    f"<{el.name}> mit tabindex=\"{value}\" hebt die natürliche "
                    "Fokus-Reihenfolge auf — tabindex entfernen (0/-1 verwenden)",
                    get_dom_path(el),
                ))
        except ValueError:
            continue
    return errors[:10]
