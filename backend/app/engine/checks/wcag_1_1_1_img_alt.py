"""WCAG 1.1.1 — Nicht-textuelle Inhalte: Bilder mit fehlendem alt-Attribut.

Fix (Review): alt="" ist per H67 ein gültiges Dekorativ-Marker — nur ein
FEHLENDES alt-Attribut ist ein Befund. role="presentation"/"none" markieren
ebenfalls dekorativ. Data-URI-Srcs werden geprüft;
URL-Dedupe entfernt c=/w=/h=-Parameter.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse

from ._base import CheckContext, finding, get_dom_path, is_accessible_element


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


async def check_img_alt(ctx: CheckContext):
    """WCAG 1.1.1 — Bilder ohne alt-Attribut (H37/H67: alt="" ist gültig)."""
    errors = []
    root = ctx.soup
    seen_urls = set()
    for img in root.find_all("img"):
        if not is_accessible_element(img):
            continue
        if (img.get("role") or "") in ("presentation", "none"):
            continue  # deklarativ dekorativ → kein alt nötig
        if img.get("alt") is not None:
            continue  # alt="" (dekorativ) oder gefüllt → gültig
        src = img.get("src", "N/A")
        normalized = _normalize_image_url(src)
        if normalized in seen_urls:
            continue
        seen_urls.add(normalized)
        errors.append(finding("WCAG_1_1_1_IMG_ALT",
                              f"src='{src}' (fehlendes alt-Attribut)", get_dom_path(img)))
    return errors
