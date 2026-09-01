"""BITV 9.1.3.5 — Eingabefelder zu Nutzerdaten vermitteln den Zweck.

Der BITV-Prüfschritt verlangt, dass Eingabefelder, die sich auf den Nutzer
selbst beziehen, ihren Zweck über ein sprachunabhängiges Attribut vermitteln —
aktuell unterstützt das ``autocomplete``-Attribut. Die Anforderung gilt nur für
Felder, die sich auf den Nutzer selbst beziehen (Login, Kontaktformulare,
Nutzerprofil etc.).

Gegenüber der WCAG-Quelle korrigiert:
- Das ``search``-Mapping wurde entfernt: Suchfelder sind keine Nutzerdaten im
  Sinne des Prüfschritts und dürfen nicht beanstandet werden, nur weil ihnen
  ``autocomplete="search"`` fehlt (kein Input Purpose aus WCAG 2.1 Abschnitt 7).
- ``_SKIP_PATTERNS`` ohne ``search``/``query``/``q``: Diese Begriffe beschreiben
  ein Suchfeld und führen zu keinem Nutzerdaten-Zweck.

Die Erkennung (Name/id/placeholder/Label → erwarteter autocomplete-Wert)
folgt der WCAG-Quelle: Mehrteilige Werte (``autocomplete="billing email"``)
sind gültig, verwaiste aria-labelledby-Referenzen zählen nicht.
"""
from __future__ import annotations

import re

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

# Erwartete autocomplete-Werte aus WCAG 2.1 Abschnitt 7 (Input Purposes).
# Dictionary nach Spezifität geordnet: generische Einträge ("name") zuletzt,
# sonst mappt z. B. "kreditkarten name" fälschlich auf "name" statt "cc-name";
# new-password vor current-password.
_AUTOCOMPLETE_MAPPING = {
    "given-name": ["vorname", "first name", "firstname", "given name", "givenname"],
    "family-name": ["nachname", "last name", "lastname", "family name", "familyname", "surname"],
    "additional-name": ["mittelname", "middle name", "middlename", "additional name"],
    "username": ["benutzername", "username", "user name", "login", "anmeldename"],
    "cc-name": ["karteninhaber", "cardholder", "kreditkarten name", "credit card name"],
    "cc-number": ["kartennummer", "card number", "kreditkartennummer", "credit card number"],
    "cc-exp": ["ablaufdatum", "expiry date", "expiration date", "gültig bis"],
    "cc-exp-month": ["ablaufmonat", "expiry month", "expiration month"],
    "cc-exp-year": ["ablaufjahr", "expiry year", "expiration year"],
    "cc-csc": ["cvv", "cvc", "sicherheitscode", "security code", "prüfziffer"],
    "bday": ["geburtsdatum", "birthday", "birth date", "date of birth", "geburtstag"],
    "bday-day": ["geburtstag", "birth day", "tag"],
    "bday-month": ["geburtsmonat", "birth month", "monat"],
    "bday-year": ["geburtsjahr", "birth year", "jahr"],
    # new-password VOR current-password — sonst matcht "neues passwort"
    # das "passwort"-Keyword von current-password.
    "new-password": ["neues passwort", "new password"],
    "current-password": ["passwort", "password", "kennwort", "aktuelles passwort", "current password"],
    "address-line1": ["adresszeile 1", "address line 1", "adresse zeile 1"],
    "address-line2": ["adresszeile 2", "address line 2", "adresse zeile 2"],
    "street-address": ["straße", "street", "adresse", "address", "strasse", "hausnummer"],
    "postal-code": ["postleitzahl", "plz", "postal code", "zip code", "zipcode"],
    "address-level2": ["stadt", "city", "ort", "gemeinde"],
    "address-level1": ["bundesland", "state", "region", "province"],
    "country-name": ["land", "country", "staat"],
    "email": ["email", "e-mail", "mail", "elektronische post", "electronic mail"],
    "tel": ["telefon", "phone", "tel", "telephone", "handy", "mobile", "festnetz"],
    "organization": ["firma", "unternehmen", "organization", "company", "organisation"],
    "organization-title": ["position", "titel", "job title", "jobtitle", "berufsbezeichnung"],
    "name": ["name", "namen", "vollständiger name", "full name"],
}

# Felder ohne erwartetes autocomplete (CAPTCHA, OTP, Kommentare, interne Felder).
# Wortgrenze = "nicht [a-z0-9]": "code" matcht "country_code" nicht mehr.
_SKIP_PATTERNS = [
    "comment", "message", "nachricht", "kommentar",
    "captcha", "security", "otp", "token", "verification",
    "custom", "other", "sonstiges", "internal", "system", "admin",
]
_SKIP_RE = re.compile(
    r"(?<![a-z0-9])(" + "|".join(re.escape(p) for p in _SKIP_PATTERNS) + r")(?![a-z0-9])",
    re.IGNORECASE,
)

_AUTOCOMPLETE_TYPES = [
    "text", "search", "url", "tel", "email", "password",
    "date", "month", "week", "time", "datetime-local", "number", "range", "color",
]


async def check_eingabefelder_zu_nutzerdaten_vermitteln_den_zweck(ctx: CheckContext):
    """BITV 9.1.3.5 — Nutzerdaten-Felder ohne (passendes) autocomplete-Attribut."""
    errors = []
    root = ctx.soup
    for inp in root.find_all("input"):
        if not is_accessible_element(inp):
            continue
        typ = inp.get("type", "text").lower()
        if typ not in _AUTOCOMPLETE_TYPES:
            continue
        autocomplete = (inp.get("autocomplete") or "").strip().lower()
        name = inp.get("name", "").lower()
        id_attr = inp.get("id", "").lower()
        placeholder = inp.get("placeholder", "").lower()

        if _SKIP_RE.search(f"{name} {id_attr} {placeholder}"):
            continue

        hints = [id_attr, " ".join(inp.get("class", [])).lower(), name, placeholder]
        if id_attr:
            label = root.find("label", {"for": inp.get("id")})
            if label:
                hints.append(label.get_text(strip=True).lower())
        parent_label = inp.find_parent("label")
        if parent_label:
            hints.append(parent_label.get_text(strip=True).lower())
        aria_label = inp.get("aria-label", "").lower()
        if aria_label:
            hints.append(aria_label)
        for lid in (inp.get("aria-labelledby") or "").split():
            el = root.find(id=lid)
            if el:
                hints.append(el.get_text(strip=True).lower())
        combined = " ".join(hints)

        expected = None
        for ac_value, keywords in _AUTOCOMPLETE_MAPPING.items():
            if any(kw in combined for kw in keywords):
                expected = ac_value
                break
        if not expected:
            continue
        tokens = autocomplete.split()
        if not tokens:
            errors.append(finding(
                "BITV_9_1_3_5_EINGABEFELDER_ZU_NUTZERDATEN_VERMITTELN_DEN_ZWECK",
                f"Eingabefeld für '{expected}' benötigt autocomplete=\"{expected}\"",
                get_dom_path(inp),
            ))
        elif expected not in tokens:
            # Mehrteilige Werte sind gültig (z. B. autocomplete="billing email").
            errors.append(finding(
                "BITV_9_1_3_5_EINGABEFELDER_ZU_NUTZERDATEN_VERMITTELN_DEN_ZWECK",
                f"Eingabefeld für '{expected}' hat autocomplete=\"{autocomplete}\", "
                f"erwartet wird Token autocomplete=\"{expected}\"",
                get_dom_path(inp),
            ))
    return errors
