"""BITV_9_2_4_4_AUSSAGEKRAEFTIGE_LINKTEXTE — Aussagekräftige Linktexte.

Übernommen aus WCAG_2_4_4_LINK_TEXT (Linkzweck aus Text/Name; AccName-Heuristik).
Ergänzt um die BITV-Ausnahme: generische Kurztexte wie "mehr", "weiter",
"weiterlesen" sind akzeptabel, wenn der programmatisch ermittelbare Kontext
(umschließender Absatz/Listenpunkt oder vorangehende Überschrift) Ziel oder
Zweck des Links benennt.

Nicht automatisiert (manuelle Bewertung): der Teil des Prüfschritts, der
prüft, ob bei Links auf nicht-HTML-Formate eine visuell gezeigte
Dateiformat-Information auch programmatisch vorliegt — das erfordert die
visuelle Erkennung von Icons/Tooltips. Ein fehlender Format-Hinweis ist laut
BITV ausdrücklich kein Mangel im Sinne dieses Prüfschritts.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding, get_dom_path, is_accessible_element
from ._helpers import resolve_accessible_name

# Nur exakte, nicht-beschreibende Kurztexte (kein Substring-Match).
_GENERIC_LINKS = {
    "hier", "hier klicken", "klicken sie hier",
    "mehr", "weiter", "weiterlesen", "weiter lesen", "mehr lesen",
    "read more", "click here", "more", "learn more",
}

# Wörter ohne inhaltliche Aussage — ein Kontext, der nur aus diesen besteht,
# benennt Ziel/Zweck des Links nicht (keine Ausnahme nach BITV 9.2.4.4).
_STOPWORDS = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "einem",
    "einen", "und", "oder", "aber", "auch", "sie", "er", "es", "ist", "sind",
    "wird", "werden", "auf", "für", "mit", "von", "zum", "zur", "im", "am",
    "an", "in", "bei", "nicht", "kein", "keine", "zu", "um", "klicken", "hier",
    "weiter", "mehr", "lesen", "the", "a", "an", "and", "of", "to", "in",
    "on", "at", "for", "with", "is", "are", "was", "be", "read", "more",
    "click", "here",
}


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _context_text(link, own_name: str) -> str:
    """Programmatisch ermittelbarer Kontext eines Links (BITV 9.2.4.4).

    Liefert den Text des nächsten umschließenden Blocks (p/li/div/td/th — div
    wird wie p behandelt) ohne den Linktext selbst; ist der leer, den Text der
    vorangehenden Überschrift (Technik H80). '' wenn kein Kontext existiert.
    """
    own_norm = _normalize(own_name)
    for parent in link.parents:
        if parent.name in ("p", "li", "div", "td", "th"):
            text = _normalize(parent.get_text(" ", strip=True))
            if own_norm:
                text = text.replace(own_norm, "", 1).strip()
            if text:
                return text
            # Kein break: ist der nächste Block nur der Link selbst, zählt der
            # Kontext des übergeordneten Blocks (BITV: bei Links in
            # untergeordneten Listen der Text des übergeordneten li-Elements).
    heading = link.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
    if heading is not None:
        text = heading.get_text(" ", strip=True)
        if text:
            return _normalize(text)
    return ""


def _is_meaningful(text: str) -> bool:
    """Kontext benennt Ziel/Zweck — enthält mindestens ein inhaltliches Wort."""
    words = _normalize(text).split()
    return any(w not in _STOPWORDS and len(w) >= 3 for w in words)


async def check_aussagekraeftige_linktexte(ctx: CheckContext) -> list[Finding]:
    """BITV_9_2_4_4 — Link ohne beschreibenden Namen oder generischer Linktext ohne Kontext."""
    errors = []
    root = ctx.soup
    for link in ctx.soup.find_all("a", href=True):
        if not is_accessible_element(link):
            continue
        name = resolve_accessible_name(link, root).strip()
        if not name:
            errors.append(finding("BITV_9_2_4_4_AUSSAGEKRAEFTIGE_LINKTEXTE",
                                  f"href='{link.get('href', 'N/A')}' (ohne Text)",
                                  get_dom_path(link)))
            continue
        if _normalize(name) in _GENERIC_LINKS:
            # BITV-Ausnahme: generischer Kurztext ist ok, wenn der Kontext
            # (Absatz/Listenpunkt/Überschrift) Ziel oder Zweck benennt.
            context = _context_text(link, name)
            if _is_meaningful(context):
                continue
            errors.append(finding("BITV_9_2_4_4_AUSSAGEKRAEFTIGE_LINKTEXTE",
                                  f"href='{link.get('href', 'N/A')}' "
                                  f"(generischer Linktext ohne Kontext: '{name}')",
                                  get_dom_path(link)))
    return errors
