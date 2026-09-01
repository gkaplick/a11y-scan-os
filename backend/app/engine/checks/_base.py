"""
Basis-Schnittstelle der Check-Module.

Jeder Check ist eine async-Funktion der Form::

    async def check_xxx(ctx: CheckContext) -> list[Finding]

- Syntax-Checks (``type == "syntax"``) nutzen ``ctx.soup`` (BeautifulSoup)
  und laufen 1× pro Seite.
- Resolution-Checks (``type == "resolution"``) nutzen ``ctx.page``
  (Playwright) + ``ctx.resolution`` und laufen pro Auflösung.

Stub-Checks (``status == "stub"``) existieren bereits mit dieser Signatur,
werfen aber ``CheckNotImplemented``. Der Runner fängt das ab und liefert
keine Findings — der Stub-Status kommt aus dem statischen Registry-Snapshot
(Tests), nicht aus dem Lauf. Ein Absturz dagegen wird geloggt (K1).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class CheckNotImplemented(NotImplementedError):
    """Wird von Stub-Checks geworfen (Kriterium architektiert, noch ohne Algorithmus)."""


@dataclass
class Finding:
    """Ein einzelner gefundener Verstoß."""

    test_id: str
    message: str = ""            # Detail-Text (was fehlt / was konkret betroffen ist)
    dom_path: str = ""           # lesbarer DOM-Pfad des betroffenen Elements
    resolution: int | None = None  # Auflösung, bei der der Fehler auftrat
    detail: str | None = None    # optionale Zusatzinfos


@dataclass
class CheckContext:
    """Alles, was ein Check für einen Lauf braucht."""

    url: str                     # aktuelle Seiten-URL
    soup: Any                    # BeautifulSoup des Seiten-DOM
    test_id: str | None = None   # id des gerade ausgeführten Kriteriums (Runner setzt sie)
    page: Any | None = None      # Playwright-Seite (für Resolution-Checks)
    resolution: int | None = None
    config: Any | None = None    # Settings (app.config.Settings)
    is_first_page: bool = False
    htaccess_user: str | None = None
    htaccess_pw: str | None = None
    # W3C-Validator (syntax check)
    w3c_enabled: bool = True
    w3c_validator_max: int = 1
    w3c_validator_url: str = "https://validator.w3.org/nu/?out=json"
    # Seitenübergreifender Job-Zustand (für Konsistenz-Checks wie Navigation/
    # Bezeichnung): pro Job ein Dict, das alle Syntax-Checks gemeinsam teilen —
    # Signaturen werden ab Seite 2 gegen die erste Seite verglichen.
    state: dict | None = None


def get_dom_path(tag: Any) -> str:
    """Lesbarer DOM-Pfad für ein BeautifulSoup-Tag.

    Baut den Pfad vom Element bis zu ``body`` auf — das direkte ``body``-Kind
    (z. B. ``main``) wird dabei mit aufgenommen, damit der Pfad den echten
    DOM-Verlauf abbildet (``body > main > section > img`` statt ``body > section
    > img``). Elemente ohne ``id`` erhalten einen Geschwisterindex
    (``:nth-of-type``), sobald gleichnamige Geschwister existieren — damit
    adressiert der Pfad das Element eindeutig (die Element-Screenshots nutzen
    ihn als Playwright-Locator).
    """
    path_parts = []
    current = tag
    while current and getattr(current, "name", None) and current.name != "[document]":
        parent = getattr(current, "parent", None)
        element_name = current.name
        if current.get("id"):
            element_name += f"#{current.get('id')}"
        if current.get("class") and len(current.get("class")) > 0:
            element_name += f".{current.get('class')[0]}"
        if not current.get("id") and parent is not None:
            siblings = [
                s for s in parent.find_all(recursive=False) if s.name == current.name
            ]
            if len(siblings) > 1:
                element_name += f":nth-of-type({siblings.index(current) + 1})"
        path_parts.insert(0, element_name)
        if parent and getattr(parent, "name", None) == "body":
            path_parts.insert(0, "body")
            break
        current = parent
    return " > ".join(path_parts)


def is_accessible_element(element: Any) -> bool:
    """Element ist nicht via aria-hidden/hidden versteckt.

    Das ``hidden``-Attribut (bzw. ein versteckter Vorfahre) blendet den
    Teilbaum aus dem Rendering aus — solche Elemente können keinen
    zugänglichen Verstoß verursachen.
    """
    def _versteckt(el: Any) -> bool:
        return el.get("aria-hidden") == "true" or el.get("hidden") is not None

    if _versteckt(element):
        return False
    current = getattr(element, "parent", None)
    while current and getattr(current, "name", None):
        if _versteckt(current):
            return False
        current = getattr(current, "parent", None)
    return True


def finding(
    test_id: str,
    message: str = "",
    dom_path: str = "",
    resolution: int | None = None,
    detail: str | None = None,
) -> Finding:
    """Komfort-Factory für Finding-Objekte."""
    return Finding(
        test_id=test_id,
        message=message,
        dom_path=dom_path,
        resolution=resolution,
        detail=detail,
    )
