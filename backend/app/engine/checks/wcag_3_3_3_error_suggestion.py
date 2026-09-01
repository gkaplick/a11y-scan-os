"""WCAG 3.3.3 — Hilfe bei Fehlern (Vorschlag zur Korrektur).

Gleiche Regel wie BITV 9.3.3.3 (AA): Wenn ein Formular Fehler automatisch
erkennt, müssen die Fehlermeldungen verständlich sein und einen Hinweis zur
Korrektur geben (z. B. erwartetes Format, Beispiel, Mindest-/Maximalangabe,
konkrete Eingabe-Aufforderung).

Heuristik: Ein Feld im Fehlerzustand (aria-invalid="true") mit zugehöriger
Fehlermeldung (aria-describedby-Ziel oder role=alert/status im Formular)
braucht in der Meldung einen Korrektur-Hinweis. Fehlerzustände OHNE Meldung
sind nicht dieser Prüfschritt (→ 3.3.1); native clientseitige Validierung
ohne Fehlerzustand ebenso wenig. Ob die Hilfe nach dem Absenden erscheint,
ist statisch nicht prüfbar — dokumentierte Grenze.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "WCAG_3_3_3_ERROR_SUGGESTION"

# Hinweis, der bei der Korrektur hilft: Beispiel, Format, Bereich,
# konkrete Aufforderung oder eine Zahl als Grenze
_HAT_HINWEIS = re.compile(
    r"z\.?\s*b\.?\b|zum beispiel|beispiel\b|format\b|mindestens\b|mind\.|maximal\b|max\.|"
    r"zwischen|bis zu|\b\d|@\w|"
    r"bitte\b.{0,40}\b(?:geben|eingeben|wähl|wahl|auswähl|auswahl|nutzen|verwend|korrigier)|"
    r"(?:nur|ausschließlich|ausschliesslich)\b.{0,30}\b(?:zulässig|erlaubt|möglich|möglich)",
    re.IGNORECASE,
)


def _fehlernachrichten(feld, form) -> list[str]:
    """Text der zu einem Feld gehörenden Fehlermeldungen."""
    out: list[str] = []
    for ref in (feld.get("aria-describedby") or "").split():
        ziel = form.find(id=ref)
        if ziel is not None:
            text = ziel.get_text(" ", strip=True)
            if text:
                out.append(text)
    for alert in form.find_all(attrs={"role": ["alert", "status"]}):
        text = alert.get_text(" ", strip=True)
        if text:
            out.append(text)
    return out


async def check_error_suggestion(ctx: CheckContext):
    """WCAG 3.3.3 — Fehlermeldung ohne Hinweis, wie der Fehler zu korrigieren ist."""
    errors = []
    for form in ctx.soup.find_all("form"):
        if not is_accessible_element(form):
            continue
        for feld in form.find_all(["input", "select", "textarea"]):
            if not is_accessible_element(feld):
                continue
            if (feld.get("aria-invalid") or "").lower() != "true":
                continue  # kein Fehlerzustand → nicht anwendbar
            nachrichten = _fehlernachrichten(feld, form)
            if not nachrichten:
                continue  # Fehlerzustand ohne Meldung → gehört zu 3.3.1
            if any(_HAT_HINWEIS.search(text) for text in nachrichten):
                continue  # mindestens eine Meldung hilft weiter
            errors.append(finding(
                _TEST_ID,
                f"Fehlermeldung ohne Korrektur-Hinweis: „{nachrichten[0][:60]}…“ — "
                "Beispiel, erwartetes Format oder konkrete Aufforderung ergänzen",
                get_dom_path(feld),
            ))
    return errors[:10]
