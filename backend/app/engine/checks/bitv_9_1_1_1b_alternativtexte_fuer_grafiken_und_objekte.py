"""BITV_9_1_1_1b_ALTERNATIVTEXTE_FUER_GRAFIKEN_UND_OBJEKTE — Alternativtexte für Grafiken und Objekte.

Quelle: docs/bitvtest/9.1.1.1b.json (WCAG 1.1.1, Level A).

Geprüft werden die im Prüfschritt genannten Objekt-Typen (Inline-SVG, object,
video/audio). Verlinkte Grafiken
und Grafiken in Bedienelementen werden in Prüfschritt 9.1.1.1a geprüft und
hier übersprungen. Dekorative Grafiken (alt="", role=presentation/none oder
aria-hidden-Teilbaum) sind gültig.

Nicht automatisiert prüfbar ist die Angemessenheit vorhandener Alternativtexte
(Abschnitt 2.7 des Prüfschritts) — sie erfordert die Bewertung durch einen
Menschen.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse

from ._base import CheckContext, finding, get_dom_path, is_accessible_element

_TEST_ID = "BITV_9_1_1_1b_ALTERNATIVTEXTE_FUER_GRAFIKEN_UND_OBJEKTE"

_FILENAME_EXT_RE = re.compile(r"[\w\-. ]+\.(?:png|jpe?g|gif|svg|webp|bmp|ico|avif)$", re.I)


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


def _ist_bedienelement(el) -> bool:
    """Grafik liegt in einem Bedienelement (Link/Button) → Prüfschritt 9.1.1.1a."""
    return el.find_parent("a") is not None or el.find_parent("button") is not None


def _ist_deklarativ_dekorativ(el) -> bool:
    """Deklarativ dekorativ: role=presentation/none bzw. aria-hidden-Teilbaum."""
    if not is_accessible_element(el):
        return True
    return (el.get("role") or "").lower() in ("presentation", "none")


def _svg_hat_alternativtext(svg) -> bool:
    """Inline-SVG hat eine Textalternative (title/desc/aria-label/labelledby)."""
    if (svg.get("aria-label") or "").strip():
        return True
    if (svg.get("aria-labelledby") or "").strip():
        return True
    return any(
        t is not None and t.get_text(strip=True)
        for t in (svg.find("title"), svg.find("desc"))
    )


def _object_hat_alternative(obj) -> bool:
    """object-Element hat Fallback-Text oder aria-label/labelledby (H53/ARIA6)."""
    if (obj.get("aria-label") or "").strip():
        return True
    if (obj.get("aria-labelledby") or "").strip():
        return True
    return bool(obj.get_text(" ", strip=True))


def _medium_hat_identifizierung(media) -> bool:
    """video/audio mit aria-label/labelledby, figcaption oder Fallback-Text."""
    if (media.get("aria-label") or "").strip():
        return True
    if (media.get("aria-labelledby") or "").strip():
        return True
    if media.get_text(" ", strip=True):
        return True
    fig = media.find_parent("figure")
    if fig is not None and fig.find("figcaption") is not None:
        return True
    return False


async def check_alternativtexte_fuer_grafiken_und_objekte(ctx: CheckContext):
    """BITV_9_1_1_1b — fehlende Alternativtexte für Grafiken und Objekte."""
    errors = []
    root = ctx.soup
    seen_urls = set()

    # 1) Unverlinkte informative <img> ohne alt-Attribut (H37/H67: alt="" gültig)
    for img in root.find_all("img"):
        if _ist_deklarativ_dekorativ(img):
            continue
        if _ist_bedienelement(img):
            continue  # gehört zu 9.1.1.1a
        src = img.get("src", "N/A")
        alt = img.get("alt")
        if alt is None:
            normalized = _normalize_image_url(src)
            if normalized in seen_urls:
                continue
            seen_urls.add(normalized)
            errors.append(finding(
                _TEST_ID,
                f"Informative Grafik ohne alt-Attribut (src='{src}')",
                get_dom_path(img),
            ))
        elif _FILENAME_EXT_RE.fullmatch(alt.strip()):
            # Bilddateiname als Alternativtext ersetzt das Bild nicht (F65/F30)
            errors.append(finding(
                _TEST_ID,
                f"Alt-Text ist ein Bilddateiname ('{alt.strip()}') statt einer "
                "beschreibenden Textalternative",
                get_dom_path(img),
            ))

    # 2) Inline-SVG ohne Textalternative (title/desc/aria-label)
    for svg in root.find_all("svg"):
        if _ist_deklarativ_dekorativ(svg):
            continue
        if _ist_bedienelement(svg):
            continue  # gehört zu 9.1.1.1a
        if svg.find_parent("svg") is not None:
            continue  # verschachteltes SVG: vom Namen des äußeren SVG abgedeckt
        if _svg_hat_alternativtext(svg):
            continue
        errors.append(finding(
            _TEST_ID,
            "Inline-SVG ohne Textalternative (title/desc/aria-label fehlen)",
            get_dom_path(svg),
        ))

    # 3) object-Element ohne Fallback-Inhalt bzw. beschreibende Alternative (H53)
    for obj in root.find_all("object"):
        if not is_accessible_element(obj):
            continue
        if _object_hat_alternative(obj):
            continue
        errors.append(finding(
            _TEST_ID,
            "Objekt (object) ohne beschreibende Alternative/Fallback-Text",
            get_dom_path(obj),
        ))

    # 4) video/audio ohne beschreibende Identifizierung (Abschnitt 2.6)
    #    Nur sichtbare Player mit controls sind eindeutig nutzerseitig relevant;
    #    dekorative Autoplay-/Hintergrund-Medien ohne controls bleiben außen vor.
    for media in root.find_all(["video", "audio"]):
        if not is_accessible_element(media):
            continue
        if media.get("controls") is None:
            continue
        if _medium_hat_identifizierung(media):
            continue
        errors.append(finding(
            _TEST_ID,
            f"<{media.name}> ohne beschreibende Identifizierung "
            "(aria-label/aria-labelledby/figcaption)",
            get_dom_path(media),
        ))

    return errors
