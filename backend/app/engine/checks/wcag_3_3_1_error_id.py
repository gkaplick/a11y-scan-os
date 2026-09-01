"""WCAG 3.3.1 — Fehlererkennung: Eingabefehler werden erkannt und im Text beschrieben.

Port des implementierten BITV-Checks 9.3.3.1 (gleicher Algorithmus,
anderer test_id). WCAG 3.3.1 (A): Fehler werden automatisch erkannt; das
fehlerhafte Feld wird identifiziert und der Fehler in Textform beschrieben.

Statisch prüfbar: Formulare, deren native Validierung ausgeschaltet ist
(novalidate), obwohl Pflichtfelder bzw. Formatprüfungen vorhanden sind
(required/pattern). Dann braucht das Formular einen eigenen, für Assistenz­
technik erkennbaren Fehler-Mechanismus:
- aria-invalid an einem Feld (Autor hat Fehlerzustand verdrahtet),
- aria-describedby, das auf einen Fehlertext verweist,
- role="alert",
- sichtbarer Fehler-Container (Klasse error/fehler/invalid).

Native Validierung (ohne novalidate) identifiziert und beschreibt Fehler
selbst → bestanden. Reine JS-Validierung ohne DOM-Signale ist statisch nicht
erkennbar — dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "WCAG_3_3_1_ERROR_ID"

_ERROR_KW = re.compile(r"(error|fehler|invalid|ungültig|ungueltig)", re.IGNORECASE)
_ERROR_CLASS = re.compile(r"(error|fehler|invalid)", re.IGNORECASE)


def _fehlermechanismus(form) -> bool:
    """Hat das Formular einen für AT erkennbaren Fehler-Anzeige-Mechanismus?"""
    for el in form.find_all(["input", "select", "textarea"]):
        if not is_accessible_element(el):
            continue
        if el.get("aria-invalid") is not None:
            return True
        describedby = el.get("aria-describedby")
        if not describedby:
            continue
        for target_id in describedby.split():
            target = form.find(id=target_id)
            if target and _ERROR_KW.search(target.get_text() or ""):
                return True

    for el in form.find_all(role="alert"):
        if is_accessible_element(el):
            return True

    # Sichtbarer Fehlertext (Klassen-Signal), aber keine Formularfelder selbst —
    # ein <input class="error"> mit Wert wäre sonst ein False Positive.
    for el in form.find_all(True):
        if el.name in ("input", "select", "textarea", "option"):
            continue
        if not is_accessible_element(el):
            continue
        klassen = " ".join(el.get("class") or [])
        if _ERROR_CLASS.search(klassen) and (el.get_text() or "").strip():
            return True

    return False


async def check_error_id(ctx: CheckContext):
    """WCAG 3.3.1 — Formular mit novalidate ohne Fehler-Anzeige-Mechanismus."""
    errors = []
    for form in ctx.soup.find_all("form"):
        if not is_accessible_element(form):
            continue
        if form.get("novalidate") is None:
            continue  # native Browser-Validierung ist aktiv → Fehler werden gemeldet

        pflichtfelder = [
            f for f in form.find_all(["input", "select", "textarea"])
            if is_accessible_element(f)
            and (f.get("required") is not None or f.get("pattern") is not None)
        ]
        if not pflichtfelder:
            continue  # keine native Fehlerquelle → Kriterium nicht anwendbar

        if _fehlermechanismus(form):
            continue

        errors.append(finding(
            _TEST_ID,
            "Formular deaktiviert die native Validierung (novalidate), bietet aber "
            "keinen erkennbaren Fehler-Anzeige-Mechanismus (aria-invalid, "
            "aria-describedby, role=alert oder sichtbarer Fehlertext)",
            get_dom_path(form),
        ))
    return errors[:10]
