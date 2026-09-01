"""BITV 9.4.1.3 — Statusmeldungen programmatisch verfügbar.

Übernommen aus WCAG 4.1.3 (``wcag_4_1_3_aria_live.check_aria_live``):
Statusmeldungen (z. B. „Warenkorb aktualisiert", „Formular abgeschickt",
„5 Suchergebnisse") müssen als ARIA-Live-Region ausgezeichnet sein, damit
assistive Technologien sie ankündigen, ohne den Fokus zu verschieben.

Automatisiert geprüft wird, ob gesetzte ``aria-live``-Werte gültig sind
(``off``/``polite``/``assertive``); Elemente in ``aria-hidden``/``hidden``-
Teilbäumen bleiben außen vor (dort ist die Live-Region nicht aktiv).

Manuell bleiben: das Identifizieren tatsächlicher Statusmeldungen (welcher
Container ist die Meldung?), die Netzwerk-Prüfung auf Seiten-Reload und die
Screenreader-Verifikation — sie erfordern Interaktion mit der Seite.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element


async def check_statusmeldungen_programmatisch_verfuegbar(ctx: CheckContext):
    """BITV 9.4.1.3 — aria-live-Wert gültig (off/polite/assertive)."""
    errors = []
    for elem in ctx.soup.find_all(attrs={"aria-live": True}):
        if not is_accessible_element(elem):
            continue
        value = (elem.get("aria-live") or "").lower()
        if value not in ["off", "polite", "assertive"]:
            errors.append(finding(
                "BITV_9_4_1_3_STATUSMELDUNGEN_PROGRAMMATISCH_VERFUEGBAR",
                f"Ungültiger aria-live-Wert '{value}' — Statusmeldungen brauchen "
                f"eine gültige Live-Region (aria-live=\"polite\"/\"assertive\" "
                f"oder role=\"status\"/\"alert\"/\"log\").",
                get_dom_path(elem),
            ))
    return errors
