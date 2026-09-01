"""WCAG 4.1.1 — Parsing: HTML-Warnungen laut W3C-Validator.

Nutzt den geteilten W3C-Lauf (_helpers) — identische Cache- und Filter-Basis
wie der Fehler-Check (wcag_4_1_1_html_error.py).
"""
from __future__ import annotations

from ._base import CheckContext
from ._helpers import _findings_for, _run_w3c


async def check_w3c_warnings(ctx: CheckContext):
    """WCAG 4.1.1 — HTML-Warnungen (4.1.1-relevant) laut Validator."""
    html_str, _errors, warnings = await _run_w3c(ctx)
    return _findings_for(warnings, ctx.soup, html_str, "WCAG_4_1_1_HTML_WARNING")
