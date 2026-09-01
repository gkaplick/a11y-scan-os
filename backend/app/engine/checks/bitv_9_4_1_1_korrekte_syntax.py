"""BITV_9_4_1_1_KORREKTE_SYNTAX — Korrekte Syntax.

Quelle: docs/bitvtest/9.4.1.1.json (WCAG 4.1.1, Level A).

Der Prüfschritt verlangt vollständige Start-/Endtags, korrekte
Verschachtelung, keine doppelten Attribute und eindeutige IDs. Geprüft wird
der geparste DOM (nicht der Quelltext vor Interpretation), gemessen über den
geteilten W3C-Validator-Lauf (_helpers._run_w3c); der 4.1.1-Filter
(_is_parsing_relevant) entspricht dem "Syntax only"-Bookmarklet des
Prüfverfahrens. Fehler und Warnungen werden gemeinsam als Befunde gemeldet.
"""
from __future__ import annotations

from ._base import CheckContext
from ._helpers import _findings_for, _run_w3c

_TEST_ID = "BITV_9_4_1_1_KORREKTE_SYNTAX"


async def check_korrekte_syntax(ctx: CheckContext):
    """BITV_9_4_1_1 — 4.1.1-relevante HTML-Fehler und -Warnungen laut W3C-Validator."""
    html_str, errors, warnings = await _run_w3c(ctx)
    return (
        _findings_for(errors, ctx.soup, html_str, _TEST_ID)
        + _findings_for(warnings, ctx.soup, html_str, _TEST_ID)
    )
