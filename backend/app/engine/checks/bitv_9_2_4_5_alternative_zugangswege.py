"""BITV 9.2.4.5 — Alternative Zugangswege.

WCAG 2.4.5 (AA): Es gibt mindestens zwei unterschiedliche Zugangswege, um zu
den Inhalten zu gelangen. Erkannte Mechanismen:
- Navigations-Landmarke: <nav> oder role="navigation" (G161),
- Suche: <input type="search">, role="search" oder Formularfeld/-aktion mit
  Suchbegriff (G125),
- Sitemap-/Inhaltsverzeichnis-Link (G63/G64).

Ohne Navigations-Landmarke zählt eine reichhaltige interne Verlinkung
(≥ 10 verschiedene interne Links) als weiterer Zugangsweg (G161). Enthält die
Seite weniger als 2 interne Links, ist sie de facto eine Einzelseite — das
Kriterium ist dann nicht anwendbar. Externe Suchdienste und per JS nachgeladene
Navigation sind statisch nicht sichtbar — dokumentierte Grenze.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from ._base import CheckContext, finding, is_accessible_element

_TEST_ID = "BITV_9_2_4_5_ALTERNATIVE_ZUGANGSWEGE"

_SITEMAP = re.compile(
    r"sitemap|site.?map|inhaltsverzeichnis|uebersicht|übersicht|seitenübersicht",
    re.IGNORECASE,
)
_SUCHFELD = re.compile(r"(such|suche|search|query)", re.IGNORECASE)


async def check_alternative_zugangswege(ctx: CheckContext):
    """BITV 9.2.4.5 — Weniger als zwei Zugangswege zu den Inhalten."""
    eigene_domain = urlparse(ctx.url).netloc

    interne_links = set()
    for a in ctx.soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if href.startswith(("http://", "https://", "//")):
            netloc = urlparse(href).netloc
            if netloc and netloc != eigene_domain:
                continue  # externer Link zählt nicht als interner Weg
        interne_links.add(href)

    if len(interne_links) < 2:
        return []  # Einzelseite: Kriterium nicht anwendbar

    mechanismen = set()

    # 1. Navigations-Landmarke (G161)
    if any(is_accessible_element(el) for el in ctx.soup.find_all("nav")):
        mechanismen.add("navigation")
    elif any(
        el.get("role") == "navigation" and is_accessible_element(el)
        for el in ctx.soup.find_all(role="navigation")
    ):
        mechanismen.add("navigation")

    # 2. Suche (G125)
    suche = False
    for el in ctx.soup.find_all(["input"]):
        if not is_accessible_element(el):
            continue
        if (el.get("type") or "").lower() == "search":
            suche = True
            break
        if _SUCHFELD.search(" ".join(filter(None, (el.get("name"), el.get("id"))))):
            suche = True
            break
    if not suche:
        for el in ctx.soup.find_all(role="search"):
            if is_accessible_element(el):
                suche = True
                break
    if not suche:
        for form in ctx.soup.find_all("form"):
            if not is_accessible_element(form):
                continue
            if _SUCHFELD.search(form.get("action") or ""):
                suche = True
                break
            if any(
                _SUCHFELD.search(" ".join(filter(None, (i.get("name"), i.get("id")))))
                for i in form.find_all(["input", "textarea"])
            ):
                suche = True
                break
    if suche:
        mechanismen.add("suche")

    # 3. Sitemap-/Inhaltsverzeichnis-Link (G63/G64)
    for a in ctx.soup.find_all("a", href=True):
        if _SITEMAP.search(a.get_text(strip=True)) or _SITEMAP.search(a["href"]):
            mechanismen.add("sitemap")
            break

    # 4. Ohne Landmarke: reichhaltige interne Verlinkung als Zugangsweg (G161)
    if "navigation" not in mechanismen and len(interne_links) >= 10:
        mechanismen.add("interne-links")

    if len(mechanismen) >= 2:
        return []

    return [finding(
        _TEST_ID,
        f"Nur {len(mechanismen)} Zugangsweg(e) erkannt — mindestens ein zweiter "
        "benötigt (Navigation, Suche oder Sitemap-Link)",
        "body",
    )]
