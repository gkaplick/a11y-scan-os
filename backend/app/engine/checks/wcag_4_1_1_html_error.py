"""WCAG 4.1.1 — Parsing: HTML-Syntaxfehler laut W3C-Validator.

Nutzt den geteilten W3C-Lauf (_helpers): content-basierter Cache, Filter auf
4.1.1-relevante Meldungen (doppelte IDs/Attribute, Tag-Struktur) und
Zeilen→DOM-Pfad-Zuordnung. Zeile/Spalte bleiben im detail-Feld.
"""
from __future__ import annotations

from ._base import CheckContext
from ._helpers import _findings_for, _run_w3c


async def check_w3c_errors(ctx: CheckContext):
    """WCAG 4.1.1 — HTML-Syntaxfehler (4.1.1-relevant) laut Validator."""
    html_str, errors, _warnings = await _run_w3c(ctx)
    return _findings_for(errors, ctx.soup, html_str, "WCAG_4_1_1_HTML_ERROR")
