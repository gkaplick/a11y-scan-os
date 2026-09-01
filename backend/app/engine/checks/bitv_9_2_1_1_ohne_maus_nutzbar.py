"""BITV 9.2.1.1 — Ohne Maus nutzbar.

Erkennt Maus-only-Bedienelemente im statischen DOM:
- Nicht-fokussierbare Elemente (ohne href/tabindex) mit onClick/mousedown/
  mouseup-Headlern (F54: „Script verwendete ein Pointer-Event als
  einziges Bedienmittel“) — sie sind weder per Tab erreichbar noch per
  Tastatur aktivierbar.
- [tabindex]-Elemente mit onClick ohne Tastatur-Aktivierungs-Handler
  (F42: Enter/Leertaste löst nicht aus).
- Hover-only-Handler (onmouseover/onmouseout) auf nicht-fokussierbaren
  Elementen.

Native fokussierbare Elemente (button/a[href]/input/…) mit onClick sind
kein Verstoß — sie sind per Tastatur bedienbar. Der Check liest das
statische HTML; per addEventListener registrierte Handler sind nicht
sichtbar und bleiben der manuellen Prüfung überlassen.
"""
from __future__ import annotations

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_2_1_1_OHNE_MAUS_NUTZBAR"

_MOUSE_AKTION = ("onclick", "ondblclick", "onmousedown", "onmouseup")
_HOVER = ("onmouseover", "onmouseout")
_TASTE = ("onkeydown", "onkeypress", "onkeyup")
_NATIV_FOKUSSIERBAR = ("a", "button", "input", "select", "textarea", "summary", "iframe")


def _ist_fokussierbar(el) -> bool:
    if el.get("disabled") is not None:
        return False
    if el.name in _NATIV_FOKUSSIERBAR:
        if el.name == "a" and not el.get("href"):
            return False
        if el.name == "input" and (el.get("type") or "text").lower() == "hidden":
            return False
        return True
    return el.has_attr("tabindex")


async def check_ohne_maus_nutzbar(ctx: CheckContext):
    """BITV 9.2.1.1 — Maus-only-Bedienelemente."""
    errors = []
    for el in ctx.soup.find_all(True):
        if not is_accessible_element(el):
            continue
        if el.name in ("html", "head", "body", "script", "style", "link", "meta", "title"):
            continue
        attrs = el.attrs
        if el.get("disabled") is not None:
            continue
        aktion = [a for a in _MOUSE_AKTION if a in attrs]
        hover = [a for a in _HOVER if a in attrs]
        if not aktion and not hover:
            continue

        if not _ist_fokussierbar(el):
            if aktion:
                errors.append(finding(
                    _TEST_ID,
                    f"<{el.name}> mit Maus-Handler ({aktion[0]}…) ist nicht fokussierbar — nur per Maus bedienbar",
                    get_dom_path(el),
                ))
            elif hover:
                errors.append(finding(
                    _TEST_ID,
                    f"<{el.name}> nur per Mouseover bedienbar (Hover-Handler ohne Fokus)",
                    get_dom_path(el),
                ))
            continue

        # Fokussierbar, aber eigenes [tabindex] ohne Tastatur-Aktivierung:
        # onClick allein ist kein Enter/Leertaste-Ersatz (F42).
        if el.has_attr("tabindex") and el.name not in _NATIV_FOKUSSIERBAR:
            if aktion and not any(t in attrs for t in _TASTE):
                errors.append(finding(
                    _TEST_ID,
                    f"<{el.name} tabindex> mit {aktion[0]} ohne Tastatur-Aktivierung (onkeydown/onkeyup)",
                    get_dom_path(el),
                ))
    return errors
