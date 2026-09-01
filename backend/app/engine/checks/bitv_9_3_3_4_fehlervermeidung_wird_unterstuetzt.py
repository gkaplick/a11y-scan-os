"""BITV 9.3.3.4 — Fehlervermeidung wird unterstützt.

WCAG 3.3.4 (AA): Bei Transaktions-Formularen (finanzielle oder rechtlich
bindende Daten) muss die Eingabe rückgängig machbar sein oder der Nutzer
vor dem Abschicken die Möglichkeit erhalten, Eingaben zu prüfen und zu
korrigieren.

Heuristik: Ein Formular mit Transaktions-Feldern (Bestellung, Zahlung, Konto,
Kreditkarte, IBAN, Steuernummer …) braucht einen Bestätigungs-/Prüf-Mechanismus:
ein Einverständnis-/Prüf-Kontrollkästchen oder einen Prüf-/Kontroll-Button.
Ohne einen solchen Mechanismus wird ein Befund gemeldet. Die Rückgängig-
Funktion nach dem Absenden ist statisch nicht prüfbar — dokumentierte Grenze.
Reine Login-/Passwort-Formulare sind keine Transaktion im Sinne von 3.3.4.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_3_3_4_FEHLERVERMEIDUNG_WIRD_UNTERSTUETZT"

# Felder, die auf eine Transaktion schließen lassen
_TRANSAKTION = re.compile(
    r"iban|bic|kontonum|konto.?nr|kredit.?karte|credit.?card|karten?nummer|"
    r"zahlung|payment|bestellung|order|checkout|warenkorb|kasse|kauf|"
    r"steuer(nummer|nr)?|invoice|rechnung",
    re.IGNORECASE,
)
# Bestätigungs-/Prüf-Mechanismus
_BESTAETIGUNG = re.compile(
    r"bestätig|bestaetig|einverstand|überprüf|ueberpruef|uberpruf|"
    r"prüf|pruf|kontroll|confirm|review",
    re.IGNORECASE,
)


def _beschriftung(el) -> str:
    return " ".join(filter(None, (
        el.get_text(strip=True),
        el.get("aria-label"),
        el.get("title"),
        el.get("name"),
        el.get("id"),
    )))


async def check_fehlervermeidung_wird_unterstuetzt(ctx: CheckContext):
    """BITV 9.3.3.4 — Transaktionsformular ohne Prüf-/Bestätigungs-Mechanismus."""
    errors = []
    for form in ctx.soup.find_all("form"):
        if not is_accessible_element(form):
            continue
        transaktions_feld = any(
            is_accessible_element(f) and _TRANSAKTION.search(_beschriftung(f))
            for f in form.find_all(["input", "select", "textarea"])
        )
        if not transaktions_feld:
            continue  # kein Transaktionsformular → nicht anwendbar

        bestaetigt = False
        # Kontrollkästchen mit Einverständnis-/Prüf-Formulierung
        for cb in form.find_all("input", type="checkbox"):
            if not is_accessible_element(cb):
                continue
            label = cb.find_parent("label")
            text = _beschriftung(cb) + (f" {label.get_text(strip=True)}" if label else "")
            if _BESTAETIGUNG.search(text):
                bestaetigt = True
                break
        # Button, der einen Prüf-/Kontroll-Schritt auslöst
        if not bestaetigt:
            for btn in form.find_all(["button", "input"]):
                if btn.get("type") not in ("submit", "button"):
                    continue
                if _BESTAETIGUNG.search(_beschriftung(btn)):
                    bestaetigt = True
                    break
        if bestaetigt:
            continue

        errors.append(finding(
            _TEST_ID,
            "Transaktionsformular (finanzielle/rechtlich bindende Daten) bietet "
            "keinen erkennbaren Prüf-/Bestätigungs-Mechanismus vor dem Absenden "
            "— Bestätigungs-Kontrollkästchen oder Prüf-Schritt ergänzen",
            get_dom_path(form),
        ))
    return errors[:10]
