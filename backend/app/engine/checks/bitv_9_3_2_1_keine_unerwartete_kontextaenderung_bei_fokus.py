"""BITV 9.3.2.1 — Keine unerwartete Kontextänderung bei Fokus.

WCAG 2.1, Technik-Fails F22/F23: Beim Erhalten des Fokus (bzw. beim Laden
der Seite) wird automatisch ein neues Fenster geöffnet, ein Formular
abgeschickt oder zu einer anderen Seite navigiert.

Erkannt werden inline-Handler:
- onfocus/onfocusin auf einem Element mit window.open/Submit/Navigation (F22),
- onload/onpageshow auf body/html mit window.open/Submit/Navigation (F23).
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_3_2_1_KEINE_UNERWARTETE_KONTEXTAENDERUNG_BEI_FOKUS"

_FOCUS_EVENTS = ("onfocus", "onfocusin", "onload", "onpageshow")
_LOAD_EVENTS = ("onload", "onpageshow")

# Kontextänderung durch Fokus/Laden: neues Fenster, Submit oder Navigation
_CONTEXT_CHANGE = re.compile(
    r"""\bwindow\.open\s*\(|\b(?:form\.)?submit\s*\(|\blocation\.href\s*=|location\.(?:assign|replace)\s*\(|window\.location\s*=""",
    re.IGNORECASE,
)


async def check_keine_unerwartete_kontextaenderung_bei_fokus(ctx: CheckContext):
    """BITV 9.3.2.1 — Fokus/Laden löst Fenster-/Submit-/Navigations-Kontextänderung aus."""
    errors = []
    for el in ctx.soup.find_all(True):
        if not is_accessible_element(el):
            continue
        # onload gilt nur für die Dokument-Wurzel (F23); onfocus für Komponenten
        if el.name in ("body", "html"):
            event_code = " ".join(filter(None, (el.get(ev) for ev in _LOAD_EVENTS)))
            trigger = "Beim Laden der Seite"
        else:
            event_code = " ".join(filter(None, (el.get(ev) for ev in _FOCUS_EVENTS)))
            if not event_code:
                continue
            trigger = f"<{el.name}> beim Fokuserhalt"
        if not event_code:
            continue
        if not _CONTEXT_CHANGE.search(event_code):
            continue
        errors.append(finding(
            _TEST_ID,
            f"{trigger} wird eine unerwartete Kontextänderung ausgelöst "
            "(Fenster öffnen / Auto-Submit / Navigation)",
            get_dom_path(el),
        ))
    return errors
