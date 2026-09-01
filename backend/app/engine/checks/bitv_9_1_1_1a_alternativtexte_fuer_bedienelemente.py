"""BITV 9.1.1.1a — Alternativtexte für Bedienelemente.

Geprüft werden nur *interaktive* Grafiken —
verlinkte Bilder, Image maps (<img usemap> + <area>), grafische Schaltflächen
(<input type="image">) und Inline-SVGs, die als Bedienelement dienen.
Nicht-verlinkte informative Grafiken gehören zu Prüfschritt 9.1.1.1b.

Ein leeres alt-Attribut ist nur dann zulässig, wenn der umgebende Link/Button
eine eigene Textalternative besitzt (H2/H30) — andernfalls ist es wie ein
fehlendes alt zu werten (Screenreader lesen sonst Dateiname/URL vor).
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse

from ._base import CheckContext, Finding, finding, get_dom_path, is_accessible_element
from ._helpers import resolve_idrefs

_TEST_ID = "BITV_9_1_1_1a_ALTERNATIVTEXTE_FUER_BEDIENELEMENTE"


def _normalize_image_url(src: str) -> str:
    """Normalisiert eine Bild-URL (entfernt c=/w=/h= Parameter) für Dedupe."""
    try:
        parsed = urlparse(src)
        params = parse_qs(parsed.query)
        filtered = {k: v for k, v in params.items() if k not in ["c", "w", "h"]}
        new_query = urlencode(filtered, doseq=True) if filtered else ""
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if new_query:
            normalized += f"?{new_query}"
        if parsed.fragment:
            normalized += f"#{parsed.fragment}"
        return normalized
    except Exception:
        return src


def _control_own_text(control) -> str:
    """Text des Links/Buttons ohne SVG-interne Beschriftungen (title/desc).

    Alternativtexte von Kind-<img> zählen als Textalternative mit (H30).
    """
    parts = []
    for node in control.find_all(string=True):
        parent = node.parent
        if parent is None or parent.find_parent("svg") is not None:
            continue
        t = node.strip()
        if t:
            parts.append(t)
    for img in control.find_all("img"):
        alt = (img.get("alt") or "").strip()
        if alt:
            parts.append(alt)
    return " ".join(parts).strip()


def _control_has_name(control, root) -> bool:
    """Link/Button hat einen zugänglichen Namen über aria-label/labelledby."""
    if (control.get("aria-label") or "").strip():
        return True
    if control.get("aria-labelledby") and resolve_idrefs(root, control.get("aria-labelledby")):
        return True
    return False


def _svg_has_accessible_name(svg, root) -> bool:
    """Inline-SVG hat eine Textalternative (title/desc/aria-label/labelledby)."""
    if (svg.get("aria-label") or "").strip():
        return True
    if svg.get("aria-labelledby") and resolve_idrefs(root, svg.get("aria-labelledby")):
        return True
    title = svg.find("title")
    if title and title.get_text(strip=True):
        return True
    desc = svg.find("desc")
    if desc and desc.get_text(strip=True):
        return True
    return False


def _has_text_alternative(el, root) -> bool:
    """Element hat eine Textalternative über alt, aria-label, title oder aria-labelledby."""
    if (el.get("alt") or "").strip():
        return True
    if (el.get("aria-label") or "").strip():
        return True
    if (el.get("title") or "").strip():
        return True
    if el.get("aria-labelledby") and resolve_idrefs(root, el.get("aria-labelledby")):
        return True
    return False


async def check_alternativtexte_fuer_bedienelemente(ctx: CheckContext) -> list[Finding]:
    """BITV 9.1.1.1a — Interaktive Grafik ohne gleichwertige Textalternative."""
    errors = []
    root = ctx.soup
    seen_urls = set()

    for img in root.find_all("img"):
        if not is_accessible_element(img):
            continue
        if (img.get("role") or "") in ("presentation", "none"):
            continue
        control = img.find_parent(["a", "button"])
        has_usemap = bool((img.get("usemap") or "").strip())
        if control is None and not has_usemap:
            continue  # nicht interaktiv → Prüfschritt 9.1.1.1b

        alt = img.get("alt")
        if alt is None:
            src = img.get("src", "N/A")
            normalized = _normalize_image_url(src)
            if normalized in seen_urls:
                continue
            seen_urls.add(normalized)
            errors.append(finding(
                _TEST_ID,
                f"Interaktive Grafik ohne alt-Attribut (src='{src}')",
                get_dom_path(img),
            ))
        elif alt == "":
            # Leeres alt nur zulässig, wenn der Link/Button selbst das Ziel/die
            # Aktion beschreibt (redundanter Link); bei Image maps immer Befund.
            if has_usemap or (
                control is not None
                and not _control_own_text(control)
                and not _control_has_name(control, root)
            ):
                errors.append(finding(
                    _TEST_ID,
                    "Interaktive Grafik mit leerem alt-Attribut ohne Textalternative im Link/Button",
                    get_dom_path(img),
                ))

    for area in root.find_all("area"):
        if not is_accessible_element(area):
            continue
        if not (area.get("href") or "").strip():
            continue  # tote Bereiche brauchen keinen Alternativtext
        if _has_text_alternative(area, root):
            continue
        errors.append(finding(
            _TEST_ID,
            "Image-map-Bereich (<area>) ohne Alternativtext (alt/aria-label)",
            get_dom_path(area),
        ))

    for inp in root.find_all("input"):
        if not is_accessible_element(inp):
            continue
        if (inp.get("type") or "text").lower() != "image":
            continue
        if _has_text_alternative(inp, root):
            continue
        errors.append(finding(
            _TEST_ID,
            "Grafische Schaltfläche (<input type=\"image\">) ohne Alternativtext (alt/aria-label)",
            get_dom_path(inp),
        ))

    for svg in root.find_all("svg"):
        if not is_accessible_element(svg):
            continue
        control = svg.find_parent(["a", "button"])
        if control is None:
            continue  # nur Bedienelemente (verlinkte/interaktive SVGs)
        if _control_own_text(control) or _control_has_name(control, root):
            continue  # Linktext/Name beschreibt das Ziel → SVG redundant
        if _svg_has_accessible_name(svg, root):
            continue
        errors.append(finding(
            _TEST_ID,
            "Inline-SVG als Bedienelement ohne Textalternative (title/desc/aria-label)",
            get_dom_path(svg),
        ))

    return errors
