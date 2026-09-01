# -*- coding: utf-8 -*-
"""Generator für die A11Y Test-Website.

Baut aus dem Kriterienkatalog ``CATALOG`` die statische Demo-/Test-Website
unter ``site/`` — eine Seite pro Kriterium und Variante
(``kriterien/<slug>-positiv.html`` / ``<slug>-negativ.html``) plus
``index.html`` und ``assets/styles.css``.

Die Website ist zugleich Demo **und** pytest-Fixture: Der Integrationstest
``backend/tests/test_testwebsite.py`` liest ``site/catalog.json`` (von
``build()`` geschrieben; der Container-Kontext hat nur ``site/``, nicht
``generate.py``) und asserted, dass jede Negativ-Seite ihre test_ids feuert
und jede Positiv-Seite sauber bleibt. Deshalb sind die Beispiele bewusst
Minimal-Markup, dessen Wirkung an den implementierten Checks ausgerichtet ist —
die Prüflogik selbst ist in ``backend/app/engine/checks/`` normativ
(Katalog: docs/BITV-WCAG-Kriterienkatalog.md).

Ausführen::

    python testwebsite/generate.py
"""
from __future__ import annotations

import html as _html
import json
import os
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent / "site"
KRITERIEN_DIR = SITE_DIR / "kriterien"
ASSETS_DIR = SITE_DIR / "assets"

ART_LABEL = {"positiv": "Positivbeispiel", "negativ": "Negativbeispiel"}
ART_KLASSE = {"positiv": "art-positiv", "negativ": "art-negativ"}


# ---------------------------------------------------------------------------
# Kontrast-Selbstcheck für das gemeinsame Styling (Chrome/Boxen/Badges).
# Die gesamte Textfarbe der Website muss AA-konform sein, damit die
# Kontrast-Checks nur die gezielten Beispiel-Stellen melden.
# ---------------------------------------------------------------------------
def _lum(hex_color: str) -> float:
    rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    conv = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * conv[0] + 0.7152 * conv[1] + 0.0722 * conv[2]


def kontrast(hex1: str, hex2: str) -> float:
    l1, l2 = _lum(hex1), _lum(hex2)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def _assert_kontrast(fg: str, bg: str, min_ratio: float, name: str) -> None:
    ratio = kontrast(fg, bg)
    assert ratio >= min_ratio, (
        f"{name}: Kontrast {fg} auf {bg} = {ratio:.2f}:1 < {min_ratio}:1"
    )


# Baseline-Farben — zentral, damit der Selbstcheck sie abdeckt.
C_TEXT = "#1a1a1a"
C_MUTED = "#4a4a4a"
C_LINK = "#0b4da6"  # 8,0:1 auf Weiß — erfüllt auch AAA (7:1), nötig für kontrast-aaa-positiv
C_FOKUS = "#005fcc"
C_WEISS = "#ffffff"
C_GRENZE = "#b8c0cc"
C_BOX_HELL = "#f2f4f8"

CSS = f"""/* A11Y Test-Website — gemeinsames, selbst konformes Styling.
   Bewusst konform: dunkle Textfarben auf hellem Grund, unterstrichene Links,
   sichtbare Fokus-Indikatoren (NIEMALS outline:none), responsive (keine festen
   Breiten), kein white-space:nowrap, keine Text-Clipping-Techniken. */
:root {{
  --text: {C_TEXT};
  --muted: {C_MUTED};
  --link: {C_LINK};
  --fokus: {C_FOKUS};
  --grenze: {C_GRENZE};
  --box-hell: {C_BOX_HELL};
}}
* {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{
  margin: 0 auto;
  padding: 1rem;
  max-width: 100%;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  line-height: 1.6;
  color: var(--text);
  background: {C_WEISS};
}}
h1, h2, h3, h4, h5, h6 {{ line-height: 1.25; }}
img, video, iframe, table, object {{ max-width: 100%; height: auto; }}
a {{ color: var(--link); text-decoration: underline; text-underline-offset: 2px; }}
a:hover {{ text-decoration-thickness: 2px; }}

/* 1.4.1 / G183 (BITV-Ausnahme): Link ohne Initial-Unterstreichung, aber mit
   Unterstreichung bei Hover/Fokus — im Initialzustand nur durch ≥ 3:1 Kontrast
   zur umgebenden Textfarbe unterscheidbar. */
.g183-link {{ text-decoration: none; }}
.g183-link:hover, .g183-link:focus, .g183-link:focus-visible {{ text-decoration: underline; }}
.g183-fail {{ text-decoration: none; }}
/* Icon nur bei Hover/Fokus (kein dauerhaftes Nicht-Farb-Merkmal → negativ). */
.icon-hover-only::before {{ content: none; }}
.icon-hover-only:hover::before, .icon-hover-only:focus::before {{ content: "↗"; }}
p, li, td, th, figcaption, dt, dd, blockquote {{ overflow-wrap: anywhere; }}
pre, code, .testid {{ overflow-wrap: anywhere; }}

/* Fokus: überall sichtbar — auch :focus, weil einige Checks programmatisch
   fokussieren (focus(focusVisible) deckt :focus-visible ab). */
a:focus, button:focus, input:focus, select:focus, textarea:focus,
[tabindex]:focus, a:focus-visible, button:focus-visible, input:focus-visible,
select:focus-visible, textarea:focus-visible, [tabindex]:focus-visible {{
  outline: 2px solid var(--fokus);
  outline-offset: 2px;
}}

/* Sprunglink: außerhalb des Viewports, wird bei Fokus eingeblendet. */
.skip-link {{
  position: absolute;
  left: -10000px;
  top: 0;
}}
.skip-link:focus, .skip-link:focus-visible {{
  left: 0;
  background: {C_WEISS};
  padding: 0.5rem 1rem;
  z-index: 1000;
}}

.seitenkopf {{ border-bottom: 1px solid var(--grenze); padding-bottom: 0.5rem; margin-bottom: 0.5rem; }}
.marke {{ font-weight: 700; font-size: 1.15rem; text-decoration: none; }}
.hauptnav {{ display: flex; flex-wrap: wrap; gap: 0.25rem 1rem; margin: 0.75rem 0 1.25rem; }}
.hauptnav a {{ padding: 0.6rem 0.25rem; }}  /* Touch-Ziel ≥ 44 px hoch (WCAG 2.5.5) */
.kategorie {{ color: var(--muted); font-size: 0.95rem; margin: 0.25rem 0 0; }}

.art-badge {{
  display: inline-block;
  padding: 0.15rem 0.6rem;
  border-radius: 3px;
  font-weight: 700;
  font-size: 0.85rem;
}}
.art-positiv {{ background: #e7f3ec; color: #14532d; }}
.art-negativ {{ background: #fbeaea; color: #7a1d1d; }}

.testids {{ margin: 0.5rem 0 1.25rem; }}
.testid {{
  display: inline-block;
  background: #eef2f7;
  color: {C_TEXT};
  border: 1px solid #c3ccd9;
  border-radius: 3px;
  padding: 0 0.4rem;
  margin: 0.15rem 0.15rem 0 0;
  font-size: 0.8rem;
  font-family: ui-monospace, "Cascadia Mono", Consolas, monospace;
}}

.beispiel {{
  margin: 1rem 0 1.5rem;
  padding: 1rem;
  border: 1px solid var(--grenze);
  border-radius: 4px;
  background: {C_BOX_HELL};
}}
.beispiel-positiv {{ border-left: 4px solid #2e7d32; background: #f6fbf7; }}
.beispiel-negativ {{ border-left: 4px solid #b3261e; background: #fbf6f6; }}
.beispiel h2, .beispiel h3 {{ margin-top: 0; }}
.hinweis {{ color: var(--muted); font-size: 0.95rem; }}

.tabelle-wrap {{ overflow-x: auto; }}
table {{
  border-collapse: collapse;
  width: 100%;
}}
th, td {{ border: 1px solid var(--grenze); padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }}
th {{ background: #eef2f7; }}

.seitenfuss {{
  margin-top: 2.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--grenze);
  color: var(--muted);
  font-size: 0.9rem;
}}
"""


# ---------------------------------------------------------------------------
# Chrome-Bausteine (gemeinsame Hülle je Seite)
# ---------------------------------------------------------------------------
def _footer_links(
    *,
    show_declaration: bool = True,
    show_sign: bool = True,
    show_easy: bool = True,
) -> str:
    """Footer-Verweise, die auf jeder Seite erreichbar sein sollen (BITV 4/7).

    „Zur Übersicht" ist immer dabei; Gebärdensprache/Leichte Sprache
    (BITV 4) und die Erklärung zur Barrierefreiheit (BITV 7) können je
    Negativbeispiel per Parameter entfernt werden. Die Zielseiten
    (erklaerung.html, gebaerdensprache.html, leichte-sprache.html) müssen
    existieren, sonst meldet der Scanner LINKS_404.
    """
    teile = ['<a href="/index.html">Zur Übersicht</a>']
    if show_sign:
        teile.append('<a href="/gebaerdensprache.html">Gebärdensprache</a>')
    if show_easy:
        teile.append('<a href="/leichte-sprache.html">Leichte Sprache</a>')
    if show_declaration:
        teile.append('<a href="/erklaerung.html">Erklärung zur Barrierefreiheit</a>')
    return " · ".join(teile)


def _chrome(
    slug: str,
    kategorie: str,
    titel: str,
    test_ids: list[str],
    art: str,
    extras: dict | None = None,
    inhalt: str = "",
) -> str:
    """Baut die komplette HTML-Seite um den ``<main>``-Inhalt ``inhalt``."""
    extras = extras or {}
    lang = extras.get("lang", "de")
    # title bewusst von "key vorhanden" vs. "key fehlt" unterschieden:
    # ein leeres title="" erzeugt ein leeres <title></title>-Tag.
    title = extras.get("title", f"{titel} ({ART_LABEL[art]}) · A11Y Test-Website")
    viewport = extras.get("viewport", "width=device-width, initial-scale=1")
    viewport_meta = (
        "" if viewport is None else f'<meta name="viewport" content="{_html.escape(viewport)}">'
    )
    style = extras.get("style", "")
    head = extras.get("head", "")
    show_nav = extras.get("show_nav", True)
    show_skip = extras.get("show_skip", True)
    show_main = extras.get("show_main", True)
    show_declaration = extras.get("show_declaration", True)
    show_sign = extras.get("show_sign_language", True)
    show_easy = extras.get("show_easy_language", True)

    skip_html = SKIP_LINK if show_skip else ""
    nav_html = (
        f'<nav aria-label="Hauptnavigation" class="hauptnav">\n'
        f'  <a href="/index.html">Startseite</a>\n'
        f'  <a href="/kriterien/{slug}-positiv.html">Positivbeispiel</a>\n'
        f'  <a href="/kriterien/{slug}-negativ.html">Negativbeispiel</a>\n'
        f"</nav>"
        if show_nav
        else ""
    )
    if show_main:
        inhalt_html = f'<main id="main">\n{inhalt}\n</main>'
    else:
        inhalt_html = f'<div class="content">\n{inhalt}\n</div>'

    badges = "\n".join(f'<span class="testid">{t}</span>' for t in test_ids)
    title_esc = _html.escape(titel)
    return f"""<!doctype html>
<html lang="{_html.escape(lang)}">
<head>
<meta charset="utf-8">
{viewport_meta}
<title>{_html.escape(title)}</title>
<link rel="stylesheet" href="/assets/styles.css">
<style>{style}</style>
{head}
</head>
<body>
{skip_html}
<header class="seitenkopf">
  <a class="marke" href="/index.html">A11Y Test-Website</a>
  <p class="kategorie">Kategorie: {_html.escape(kategorie)}</p>
</header>
{nav_html}
{inhalt_html}
<footer class="seitenfuss">
  <p>A11Y Test-Website · {ART_LABEL[art]} · {_footer_links(show_declaration=show_declaration, show_sign=show_sign, show_easy=show_easy)}</p>
</footer>
</body>
</html>"""


def _beschriftung(kategorie: str, titel: str, test_ids: list[str], art: str, beschreibung: str) -> str:
    art_klasse = ART_KLASSE[art]
    art_label = ART_LABEL[art]
    badges = "\n".join(f'<span class="testid">{t}</span>' for t in test_ids)
    return f"""<span class="art-badge {art_klasse}">{art_label}</span>
<p class="kategorie">Kategorie: {_html.escape(kategorie)}</p>
<h1>{_html.escape(titel)}</h1>
<p class="beschreibung">{_html.escape(beschreibung)}</p>
<p class="testids">Geprüfte Kriterien: {badges}</p>
"""


def _partner_links(slug: str, art: str) -> str:
    """Querverweis auf die jeweils andere Variante."""
    if art == "positiv":
        return f'<p class="hinweis">Zur Gegenprobe: <a href="/kriterien/{slug}-negativ.html">Negativbeispiel ansehen</a></p>'
    return f'<p class="hinweis">Zur Gegenprobe: <a href="/kriterien/{slug}-positiv.html">Positivbeispiel ansehen</a></p>'


# ---------------------------------------------------------------------------
# Startseite
# ---------------------------------------------------------------------------
def _index_html() -> str:
    sections: list[str] = []
    kategorien_ord: list[tuple[str, list[dict]]] = []
    for k in CATALOG:
        if not kategorien_ord or kategorien_ord[-1][0] != k["kategorie"]:
            kategorien_ord.append((k["kategorie"], []))
        kategorien_ord[-1][1].append(k)

    for kategorie, kriterien in kategorien_ord:
        items = []
        for k in kriterien:
            badges = " ".join(f'<span class="testid">{t}</span>' for t in k["test_ids"])
            items.append(
                f'<li class="kriterium">\n'
                f'  <h3>{_html.escape(k["titel"])}</h3>\n'
                f'  <p>{_html.escape(k["beschreibung"])}</p>\n'
                f'  <p class="testids">{badges}</p>\n'
                f'  <p class="links">\n'
                f'    <a href="/kriterien/{k["slug"]}-positiv.html">Positivbeispiel</a> · '
                f'<a href="/kriterien/{k["slug"]}-negativ.html">Negativbeispiel</a>\n'
                f"  </p>\n"
                f"</li>"
            )
        sections.append(
            f'<section class="kategorie">\n'
            f'  <h2>{_html.escape(kategorie)}</h2>\n'
            f'  <ul class="kriterien-liste">\n' + "\n".join(items) + f"\n  </ul>\n"
            f"</section>"
        )

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>A11Y Test-Website · Positiv-/Negativbeispiele je Prüfkriterium</title>
<link rel="stylesheet" href="/assets/styles.css">
</head>
<body>
<a class="skip-link" href="#main">Zum Inhalt springen</a>
<header class="seitenkopf">
  <a class="marke" href="/index.html">A11Y Test-Website</a>
</header>
<nav aria-label="Hauptnavigation" class="hauptnav">
  <a href="/index.html">Startseite</a>
</nav>
<form role="search" class="suche">
  <label for="suche-index">Suche</label>
  <input id="suche-index" name="suche" type="search">
</form>
<main id="main">
  <h1>A11Y Test-Website</h1>
  <p>Diese Website enthält zu jedem automatisiert prüfbaren Kriterium des
  Scanners ein <strong>Positivbeispiel</strong> (konform, soll keine Befunde
  erzeugen) und ein <strong>Negativbeispiel</strong> (Verstoß, soll genau die
  gelisteten Kriterien melden). Scanne sie mit Suite „Alle“ unter
  <code>http://localhost:8099</code>.</p>
  <p class="hinweis">Hinweis: Die Beispiele sind Minimal-Markup zur
  Veranschaulichung und Absicherung — kein vollwertiges Barrierefreiheits-Muster
  für reale Websites. Normative Quelle der Kriterien ist der
  BITV/WCAG-Kriterienkatalog.</p>
  {os.linesep.join(sections)}
</main>
<footer class="seitenfuss">
  <p>A11Y Test-Website · {_footer_links()}</p>
</footer>
</body>
</html>"""


def _angebot_seite(title: str, haupt: str, text: str) -> str:
    """Schlanke Angebotsseite (Gebärdensprache/Leichte Sprache) mit vollem Footer."""
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · A11Y Test-Website</title>
<link rel="stylesheet" href="/assets/styles.css">
</head>
<body>
<a class="skip-link" href="#main">Zum Inhalt springen</a>
<header class="seitenkopf">
  <a class="marke" href="/index.html">A11Y Test-Website</a>
</header>
<nav aria-label="Hauptnavigation" class="hauptnav">
  <a href="/index.html">Startseite</a>
</nav>
<main id="main">
  <h1>{haupt}</h1>
  <p>{text}</p>
</main>
<footer class="seitenfuss">
  <p>A11Y Test-Website · {_footer_links()}</p>
</footer>
</body>
</html>"""


def _gebaerdensprache_html() -> str:
    return _angebot_seite(
        "Gebärdensprache",
        "Gebärdensprach-Video",
        "Die wichtigsten Inhalte dieser Website stehen auch als Video in "
        "Deutscher Gebärdensprache (DGS) zur Verfügung.",
    )


def _leichte_sprache_html() -> str:
    return _angebot_seite(
        "Leichte Sprache",
        "Leichte Sprache",
        "Die wichtigsten Inhalte dieser Website stehen auch in Leichter "
        "Sprache zur Verfügung.",
    )


def _erklaerung_html() -> str:
    """Zielseite des Footer-Links der Erklärung zur Barrierefreiheit (BITV 7).

    Eigene, schlanke Seite (kein _chrome mit Nav-zu-Bestandsseiten): Der
    Verweis muss existieren, sonst meldet der Scanner LINKS_404 auf allen
    Seiten. Titel/Überschrift tragen den Katalog-Begriff, damit der
    BITV-7-Check die Seite als „selbst die Erklärung" erkennt.
    """
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Erklärung zur Barrierefreiheit · A11Y Test-Website</title>
<link rel="stylesheet" href="/assets/styles.css">
</head>
<body>
<a class="skip-link" href="#main">Zum Inhalt springen</a>
<header class="seitenkopf">
  <a class="marke" href="/index.html">A11Y Test-Website</a>
</header>
<nav aria-label="Hauptnavigation" class="hauptnav">
  <a href="/index.html">Startseite</a>
</nav>
<main id="main">
  <h1>Erklärung zur Barrierefreiheit</h1>
  <p>Diese Test-Website bemüht sich, die Anforderungen der BITV 2.0 und der
  WCAG 2.1 zu erfüllen. Redaktionell gepflegt im Rahmen des
  Scanner-Projekts.</p>
</main>
<footer class="seitenfuss">
  <p>A11Y Test-Website · {_footer_links()}</p>
</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def _catalog_export() -> list[dict]:
    """JSON-serialisierbare Katalog-Ansicht — Wahrheitsquelle für den Test.

    ``site/catalog.json`` wird mit der Website geschrieben, damit der
    Integrationstest auch **im Container** (dort liegt nur ``site/``,
    nicht ``generate.py``) die slug→test_ids-Zuordnung kennt.
    """
    out: list[dict] = []
    for k in CATALOG:
        out.append(
            {
                "slug": k["slug"],
                "kategorie": k["kategorie"],
                "titel": k["titel"],
                "beschreibung": k["beschreibung"],
                "test_ids": k["test_ids"],
                "pytest": k.get("pytest", True),
                "seiten": {art: f"kriterien/{k['slug']}-{art}.html" for art in ("positiv", "negativ")},
            }
        )
    return out


def build() -> None:
    """Schreibt die vollständige Website nach site/ (inkl. catalog.json)."""
    # Kontrast-Selbstcheck der Baseline-Farben (AA ≥ 4,5:1).
    for fg, name in ((C_TEXT, "Text"), (C_MUTED, "Muted"), (C_LINK, "Link")):
        _assert_kontrast(fg, C_WEISS, 4.5, name)
    # Link-Farbe zusätzlich AAA-konform (≥ 7:1) — die Positiv-Seite
    # kontrast-aaa muss frei von WCAG_1_4_6 bleiben (die Links im Chrome
    # sind Teil des gescannten Texts).
    _assert_kontrast(C_LINK, C_WEISS, 7.0, "Link (AAA)")

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    KRITERIEN_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    (ASSETS_DIR / "styles.css").write_text(CSS, encoding="utf-8")
    (SITE_DIR / "index.html").write_text(_index_html(), encoding="utf-8")
    (SITE_DIR / "erklaerung.html").write_text(_erklaerung_html(), encoding="utf-8")
    (SITE_DIR / "gebaerdensprache.html").write_text(_gebaerdensprache_html(), encoding="utf-8")
    (SITE_DIR / "leichte-sprache.html").write_text(_leichte_sprache_html(), encoding="utf-8")

    slugs: list[str] = []
    for k in CATALOG:
        slug = k["slug"]
        slugs.append(slug)
        for art in ("positiv", "negativ"):
            extras = k.get(f"extras_{art}", {})
            test_ids = k["test_ids"]
            inhalt = _beschriftung(k["kategorie"], k["titel"], test_ids, art, k["beschreibung"])
            inhalt += k[f"{art}_html"]
            inhalt += _partner_links(slug, art)
            page = _chrome(slug, k["kategorie"], k["titel"], test_ids, art, extras, inhalt)
            (KRITERIEN_DIR / f"{slug}-{art}.html").write_text(page, encoding="utf-8")

    # Katalog-Export: eine Wahrheitsquelle für den Integrationstest (Container).
    (SITE_DIR / "catalog.json").write_text(
        json.dumps(_catalog_export(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Website generiert: {SITE_DIR} ({len(slugs)} Kriterien, {len(slugs) * 2} Seiten + catalog.json)")


# Sprunglink-Baustein (im Chrome, sofern nicht per extras deaktiviert).
SKIP_LINK = '<a class="skip-link" href="#main">Zum Inhalt springen</a>'


# ---------------------------------------------------------------------------
# Katalog-Helfer
# ---------------------------------------------------------------------------
# 1×1-Transparent-GIF als data:-URI: Bilder laden ohne Netz und ohne 404.
DATA_GIF = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"


def _beispiel(art: str, inhalt: str, titel: str | None = None) -> str:
    """Beispiel-Box mit Überschrift; ``titel=None`` → ohne <h2>.

    Ohne <h2> für kontextfreie Linktexte (BITV 9.2.4.4 wertet den
    umgebenden Block als Kontext — ein Titel würde den Befund verhindern).
    """
    kl = ART_KLASSE[art]
    h2 = f"<h2>{_html.escape(titel)}</h2>\n" if titel else ""
    return f'<div class="beispiel {kl}">\n{h2}{inhalt}\n</div>'


def _beispiele(*blocks: str) -> str:
    """Mehrere Beispiel-Boxen, durch Leerzeile getrennt."""
    return "\n\n".join(blocks)


def _video_figure(src: str, *, autoplay: bool = False, muted: bool = False,
                  controls: bool = False, captions: bool = False,
                  descriptions: bool = False, transcript: bool = False,
                  ad_btn: bool = False, caption: str = "Produktvideo") -> str:
    """Figur mit <video> — Tracks/Steuerungen nur, wo gezielt gesetzt.

    Die Track-Urls existieren nicht (kein 404-Befund: der Crawler folgt nur
    <a href>-Links). ``transcript`` fügt einen Skip-/Transkript-Link mit
    Fragment-Ziel hinzu (von WCAG 1.2.1 als Transkript gewertet).
    """
    attrs = [f'src="{src}"']
    if autoplay:
        attrs.append("autoplay")
    if muted:
        attrs.append("muted")
    if controls:
        attrs.append("controls")
    tracks = ""
    if captions:
        tracks += '\n    <track kind="captions" src="untertitel.vtt">'
    if descriptions:
        tracks += '\n    <track kind="descriptions" src="audiodeskription.vtt">'
    extra = ""
    if ad_btn:
        extra += '\n  <button type="button">Audiodeskription</button>'
    if transcript:
        extra += '\n  <p><a href="#transkript">Transkript anzeigen</a></p>'
    return (
        f'<figure class="media">\n'
        f'  <video {" ".join(attrs)}>{tracks}\n  </video>\n'
        f'  <figcaption>{_html.escape(caption)}</figcaption>\n'
        f'{extra}\n'
        f'</figure>'
    )


def _audio_figure(src: str, *, autoplay: bool = False, controls: bool = False,
                  transcript: bool = False, caption: str = "Audio-Hörprobe") -> str:
    """Figur mit <audio>."""
    attrs = [f'src="{src}"']
    if autoplay:
        attrs.append("autoplay")
    if controls:
        attrs.append("controls")
    extra = ""
    if transcript:
        extra += '\n  <p><a href="#transkript">Transkript anzeigen</a></p>'
    return (
        f'<figure class="media">\n'
        f'  <audio {" ".join(attrs)}></audio>\n'
        f'  <figcaption>{_html.escape(caption)}</figcaption>\n'
        f'{extra}\n'
        f'</figure>'
    )


# ---------------------------------------------------------------------------
# Kriterienkatalog
# ---------------------------------------------------------------------------
# Pro Kriterium:
#   slug, kategorie, titel, beschreibung, test_ids,
#   positiv_html, negativ_html  (der <main>-Inhalt ohne <main>/Chrome),
#   extras_positiv / extras_negativ (optional: lang, title, viewport, style,
#     head, show_nav, show_skip, show_main),
#   pytest=False  → vom Integrationstest übersprungen (nur W3C-basiert).
# Die test_ids sind die exakten Befund-IDs der Check-Dateien (Engine-Quelle);
# Norm-Referenzen (Level, BITV-Nummer) stehen im Kriterienkatalog.
CATALOG: list[dict] = [
    # ── Bilder & Grafiken ────────────────────────────────────────────────
    {
        "slug": "img-alt",
        "kategorie": "Bilder & Grafiken",
        "titel": "Alternativtexte für Bilder",
        "beschreibung": "Informative Bilder brauchen ein alt-Attribut; rein dekorative Bilder ein leeres alt=\"\".",
        "test_ids": ["WCAG_1_1_1_IMG_ALT"],
        "positiv_html": _beispiel("positiv",
            f'<p><img src="{DATA_GIF}" alt="Beschreibung des Bildes"></p>\n'
            f'<p><img src="{DATA_GIF}" alt=""></p>',
            "Bilder mit Alt-Text"),
        "negativ_html": _beispiel("negativ",
            f'<p><img src="{DATA_GIF}"></p>',
            "Bild ohne alt-Attribut"),
    },
    {
        "slug": "bedienelement-alt",
        "kategorie": "Bilder & Grafiken",
        "titel": "Alternativtexte für Bedienelemente",
        "beschreibung": "Grafiken in Links/Buttons sowie grafische Schaltflächen (input type=image) brauchen eine Textalternative.",
        "test_ids": ["BITV_9_1_1_1a_ALTERNATIVTEXTE_FUER_BEDIENELEMENTE"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                f'<p><a href="/index.html"><img src="{DATA_GIF}" alt="Zum Bericht"></a></p>',
                "Link-Grafik mit Alt-Text"),
            _beispiel("positiv",
                f'<p><input type="image" src="{DATA_GIF}" alt="Suchen"></p>',
                "Grafische Schaltfläche mit Alt-Text"),
        ),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                f'<p><a href="/index.html"><img src="{DATA_GIF}"></a></p>',
                "Link-Grafik ohne Alt-Text"),
            _beispiel("negativ",
                f'<p><input type="image" src="{DATA_GIF}" alt=""></p>',
                "Grafische Schaltfläche ohne Alt-Text"),
        ),
    },
    {
        "slug": "grafik-alt",
        "kategorie": "Bilder & Grafiken",
        "titel": "Alternativtexte für Grafiken und Objekte",
        "beschreibung": "Unverlinkte informative Grafiken, Inline-SVGs und Objekte brauchen eine Textalternative.",
        "test_ids": ["BITV_9_1_1_1b_ALTERNATIVTEXTE_FUER_GRAFIKEN_UND_OBJEKTE"],
        "positiv_html": _beispiel("positiv",
            f'<figure><img src="{DATA_GIF}" alt="Das Team"><figcaption>Unser Team</figcaption></figure>',
            "Grafik mit Alt-Text und Legende"),
        "negativ_html": _beispiele(
            _beispiel("negativ", f'<p><img src="{DATA_GIF}"></p>', "Informative Grafik ohne Alt-Text"),
            _beispiel("negativ",
                '<p><object type="application/x-shockwave-flash" data="animation.swf"></object></p>',
                "Objekt ohne Fallback-Text"),
        ),
    },
    {
        "slug": "layout-grafik-alt",
        "kategorie": "Bilder & Grafiken",
        "titel": "Leere Alt-Attribute für Layoutgrafiken",
        "beschreibung": "Dekorative Grafiken brauchen alt=\"\" ohne title; Füll-Alt-Texte wie „spacer“ sind zu vermeiden.",
        "test_ids": ["BITV_9_1_1_1c_LEERE_ALT_ATTRIBUTE_FUER_LAYOUTGRAFIKEN"],
        "positiv_html": _beispiele(
            _beispiel("positiv", f'<p><img src="{DATA_GIF}" alt=""></p>', "Dekoratives Bild mit leerem alt"),
            _beispiel("positiv",
                '<svg aria-hidden="true" width="16" height="16"><circle cx="8" cy="8" r="6"/></svg>',
                "Dekoratives SVG versteckt"),
        ),
        "negativ_html": _beispiele(
            _beispiel("negativ", f'<p><img src="{DATA_GIF}" alt="" title="Deko"></p>', "alt=\"\" mit nicht-leerem title"),
            _beispiel("negativ", f'<p><img src="{DATA_GIF}" alt="spacer"></p>', "Füll-Alt-Text"),
        ),
    },

    # ── Medien & Video ───────────────────────────────────────────────────
    {
        "slug": "audio-transkript",
        "kategorie": "Medien & Video",
        "titel": "Transkript für Audio-Inhalte",
        "beschreibung": "Reine Audio- und Video-Inhalte brauchen ein verlinktes Transkript.",
        "test_ids": ["WCAG_1_2_1_AUDIO_TRANSCRIPT"],
        "positiv_html": _beispiel("positiv",
            _audio_figure("a.mp3", controls=True, transcript=True),
            "Audio mit verlinktem Transkript"),
        "negativ_html": _beispiel("negativ",
            _audio_figure("a.mp3", controls=True),
            "Audio ohne Transkript"),
    },
    {
        "slug": "video-untertitel",
        "kategorie": "Medien & Video",
        "titel": "Untertitel für aufgezeichnete Videos",
        "beschreibung": "Videos mit Ton brauchen eine Untertitel-Spur (track kind=\"captions\") oder eine Textalternative.",
        "test_ids": ["WCAG_1_2_2_CAPTIONS", "BITV_9_1_2_2_AUFGEZEICHNETE_VIDEOS_MIT_UNTERTITELN"],
        "positiv_html": _beispiel("positiv",
            _video_figure("v.mp4", controls=True, captions=True, descriptions=True,
                          transcript=True, ad_btn=True),
            "Video mit Untertiteln"),
        "negativ_html": _beispiel("negativ",
            _video_figure("v.mp4", controls=True, descriptions=True, ad_btn=True),
            "Video ohne Untertitel-Spur"),
    },
    {
        "slug": "video-audiodeskription",
        "kategorie": "Medien & Video",
        "titel": "Audiodeskription für Videos",
        "beschreibung": "Videos brauchen eine Audiodeskriptions-Spur (track kind=\"descriptions\") oder als Alternative einen Hinweistext.",
        "test_ids": ["WCAG_1_2_5_AD", "EN_7_2_1_AD_PLAYBACK", "BITV_9_1_2_5_AUDIODESKRIPTION_FUER_VIDEOS"],
        "positiv_html": _beispiel("positiv",
            _video_figure("v.mp4", controls=True, captions=True, descriptions=True,
                          transcript=True, ad_btn=True),
            "Video mit Audiodeskription"),
        "negativ_html": _beispiel("negativ",
            _video_figure("v.mp4", controls=True, captions=True, transcript=True, ad_btn=True),
            "Video ohne Audiodeskriptions-Spur"),
    },
    {
        "slug": "autoplay-ton",
        "kategorie": "Medien & Video",
        "titel": "Kein automatisch abgespielter Ton",
        "beschreibung": "Autoplay ist nur ohne Ton erlaubt: Videos müssen muted sein, Audio darf nicht automatisch starten.",
        "test_ids": ["WCAG_1_4_2_AUTOPLAY", "BITV_9_1_4_2_TON_ABSCHALTBAR"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                _video_figure("v.mp4", autoplay=True, muted=True, controls=True,
                              captions=True, descriptions=True, transcript=True, ad_btn=True),
                "Video mit muted-Autoplay"),
            _beispiel("positiv",
                _audio_figure("a.mp3", controls=True, transcript=True),
                "Audio ohne Autoplay"),
        ),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                _video_figure("v.mp4", autoplay=True, controls=True,
                              captions=True, descriptions=True, transcript=True, ad_btn=True),
                "Video mit Autoplay ohne muted"),
            _beispiel("negativ",
                _audio_figure("a.mp3", autoplay=True, controls=True, transcript=True),
                "Audio mit Autoplay"),
        ),
    },
    {
        "slug": "iframe-titel",
        "kategorie": "Medien & Video",
        "titel": "Titel für Iframes",
        "beschreibung": "Eingebettete Inhalte (iframe) brauchen einen beschreibenden Titel.",
        "test_ids": ["WCAG_2_4_1_IFRAME_TITLE"],
        "positiv_html": _beispiel("positiv",
            '<iframe src="/index.html" title="Übersicht über die Test-Website"></iframe>',
            "Iframe mit Titel"),
        "negativ_html": _beispiel("negativ",
            '<iframe src="/index.html"></iframe>',
            "Iframe ohne Titel"),
    },
    {
        "slug": "video-titel",
        "kategorie": "Medien & Video",
        "titel": "Titel für eingebettete Videos",
        "beschreibung": "Eingebettete Videos (YouTube, Vimeo, …) brauchen ein beschreibendes iframe-title-Attribut.",
        "test_ids": ["WCAG_2_4_1_VIDEO_TITLE", "WCAG_2_4_1_IFRAME_TITLE"],
        "positiv_html": _beispiel("positiv",
            '<iframe title="Einführungsvideo zum Produkt" src="https://www.youtube.com/embed/pq-xyz123"></iframe>',
            "Video-Iframe mit Titel"),
        "negativ_html": _beispiel("negativ",
            '<iframe src="https://www.youtube.com/embed/pq-xyz123"></iframe>',
            "Video-Iframe ohne Titel"),
    },
    {
        "slug": "video-bedienelemente",
        "kategorie": "Medien & Video",
        "titel": "Player-Steuerung für Untertitel und Audiodeskription",
        "beschreibung": "Video-/Audioplayer müssen Untertitel und Audiodeskription bedienbar machen (controls bzw. eigene Buttons).",
        "test_ids": ["EN_7_3_CONTROLS"],
        "positiv_html": _beispiel("positiv",
            _video_figure("v.mp4", controls=True, captions=True, descriptions=True,
                          transcript=True, ad_btn=True),
            "Player mit Steuerungen"),
        "negativ_html": _beispiel("negativ",
            _video_figure("v.mp4", captions=True, descriptions=True),
            "Player ohne Steuerungen"),
    },

    # ── Kontrast & Farbe ─────────────────────────────────────────────────
    {
        "slug": "kontrast-aa",
        "kategorie": "Kontrast & Farbe",
        "titel": "Kontrast von Text (AA)",
        "beschreibung": "Text muss mindestens 4,5:1 (großer Text 3:1) Kontrast zum Hintergrund haben.",
        "test_ids": ["WCAG_1_4_3_CONTRAST_AA", "BITV_9_1_4_3_KONTRASTE_VON_TEXTEN_AUSREICHEND"],
        "positiv_html": _beispiel("positiv",
            '<p>Text mit ausreichendem Kontrast (<span style="color:#333">dunkelgrau auf Weiß</span>).</p>',
            "Ausreichender Kontrast"),
        "negativ_html": _beispiel("negativ",
            '<p style="color:#7A7A7A">Dieser Text hat zu wenig Kontrast zum Hintergrund.</p>',
            "Zu geringer Kontrast (AA)"),
    },
    {
        "slug": "kontrast-aaa",
        "kategorie": "Kontrast & Farbe",
        "titel": "Kontrast von Text (AAA)",
        "beschreibung": "Erhöhter Kontrast (7:1 bzw. 4,5:1 für großen Text) über die gesetzliche Pflicht hinaus.",
        "test_ids": ["WCAG_1_4_6_CONTRAST_AAA"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                '<p>Text mit AAA-Kontrast (<span style="color:#333">dunkelgrau auf Weiß</span>).</p>',
                "Normale Schrift"),
            _beispiel("positiv",
                '<p style="color:#5a5a5a;font-size:1.5rem">Großer Text (24&nbsp;px) erfüllt AAA-large.</p>',
                "Große Schrift"),
        ),
        "negativ_html": _beispiel("negativ",
            '<p style="color:#6f6f6f">Dieser Text erfüllt AA, aber nicht den erhöhten AAA-Kontrast.</p>',
            "Zu geringer Kontrast (AAA)"),
    },
    {
        "slug": "links-nicht-nur-farbe",
        "kategorie": "Kontrast & Farbe",
        "titel": "Information nicht nur durch Farbe",
        "beschreibung": "Links müssen sich außer durch die Farbe durch ein dauerhaftes Nicht-Farb-Merkmal vom Text abheben (Unterstreichung, Fettung ab halbfett, Marker-Hintergrund, Icon) — oder bei ≥ 3:1 Kontrast zur umgebenden Textfarbe bei Hover/Fokus zusätzlich hervorgehoben werden (BITV/G183-Ausnahme).",
        "test_ids": ["WCAG_1_4_1_COLOR_ONLY", "BITV_9_1_4_1_OHNE_FARBEN_NUTZBAR"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                '<p>Weitere Informationen finden Sie <a href="/index.html">unter diesem Link</a>.</p>',
                "Unterstrichener Link"),
            _beispiel("positiv",
                '<p>Details stehen im <a href="/index.html" style="color:#555;text-decoration:none;font-weight:600">hervorgehobenen Dokument</a>.</p>',
                "Halbfetter Link (Schriftdicke)"),
            _beispiel("positiv",
                '<p>Details stehen im <a href="/index.html" style="color:#0b4da6;text-decoration:none;background-color:#e6f0ff">markierten Dokument</a>.</p>',
                "Link mit eigener Hintergrundfarbe (Marker)"),
            _beispiel("positiv",
                '<p>Mehr dazu: <a href="/index.html" style="color:#555;text-decoration:none">Handbuch lesen ↗</a>.</p>',
                "Link mit festem Icon (Pfeil)"),
            _beispiel("positiv",
                '<p style="color:#666">Die Details finden Sie im <a class="g183-link" href="/index.html" style="color:#000">Zusatzdokument</a>.</p>',
                "G183: ≥ 3:1 Kontrast + Unterstreichung bei Hover/Fokus"),
            _beispiel("positiv",
                '<p>Details stehen im <a href="/index.html" style="text-decoration:none;border:1px solid #0b4da6;padding:2px 6px">gerahmten Dokument</a>.</p>',
                "Link mit Rahmen (Border)"),
            _beispiel("positiv",
                '<p>Details stehen im <a href="/index.html" style="text-decoration:none;font-style:italic">kursiven Dokument</a>.</p>',
                "Kursiver Link (Font-Style)"),
            _beispiel("positiv",
                '<p>Anleitung: <a href="/index.html" style="text-decoration:none;color:#555"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg> Werkzeug anwenden</a>.</p>',
                "Link mit eingebettetem SVG-Icon"),
        ),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<p>Weitere Informationen finden Sie <a href="/index.html" style="color:#555;text-decoration:none">in den Unterlagen</a>.</p>',
                "Link nur durch Farbe erkennbar (Kontrast < 3:1)"),
            _beispiel("negativ",
                '<p style="color:#666">Die Details finden Sie im <a class="g183-fail" href="/index.html" style="color:#000">Zusatzdokument</a>.</p>',
                "≥ 3:1 Kontrast, aber ohne Hover/Fokus-Unterstreichung"),
            _beispiel("negativ",
                '<p>Weiter im <a class="icon-hover-only" href="/index.html" style="color:#555;text-decoration:none">Handbuch</a>.</p>',
                "Icon erscheint nur bei Hover (nicht dauerhaft)"),
        ),
    },

    # ── Überschriften ────────────────────────────────────────────────────
    {
        "slug": "heading-hierarchie",
        "kategorie": "Überschriften",
        "titel": "Überschriften-Hierarchie",
        "beschreibung": "Überschriften dürfen keine Ebenen überspringen (z. B. h2 → h4).",
        "test_ids": ["WCAG_1_3_1_HEADING_SKIP"],
        "positiv_html": _beispiel("positiv",
            '<h2>Unterabschnitt</h2><p>Text der Ebene 2.</p><h3>Unter-Unterabschnitt</h3><p>Text der Ebene 3.</p>',
            "Lückenlose Hierarchie"),
        "negativ_html": _beispiel("negativ",
            '<h2>Unterabschnitt</h2><p>Text der Ebene 2.</p><h4>Übersprungene Ebene</h4><p>Text der Ebene 4.</p>',
            "Sprung von h2 zu h4"),
    },
    {
        "slug": "heading-aria-level",
        "kategorie": "Überschriften",
        "titel": "ARIA-Überschriften mit Ebene",
        "beschreibung": "role=\"heading\" braucht ein gültiges aria-level.",
        "test_ids": ["BITV_9_1_3_1a_HTML_STRUKTURELEMENTE_FUER_UEBERSCHRIFTEN"],
        "positiv_html": _beispiel("positiv",
            '<div role="heading" aria-level="2">Unterabschnitt als ARIA-Überschrift</div>',
            "role=heading mit aria-level"),
        "negativ_html": _beispiel("negativ",
            '<div role="heading">Überschrift ohne aria-level</div>',
            "role=heading ohne aria-level"),
    },
    {
        "slug": "leere-ueberschrift",
        "kategorie": "Überschriften",
        "titel": "Aussagekräftige Überschriften",
        "beschreibung": "Überschriften dürfen nicht leer sein und brauchen einen Text bzw. ein alt/aria-label.",
        "test_ids": ["WCAG_2_4_6_EMPTY_HEADING", "BITV_9_2_4_6_AUSSAGEKRAEFTIGE_UEBERSCHRIFTEN_UND_BESCHRIFTUNGEN"],
        "positiv_html": _beispiele(
            _beispiel("positiv", '<h2>Über uns</h2>', "Überschrift mit Text"),
            _beispiel("positiv", '<h3 aria-label="Kontakt">Kontakt aufnehmen</h3>', "Überschrift mit aria-label"),
        ),
        "negativ_html": _beispiel("negativ",
            '<h2></h2>',
            "Leere Überschrift"),
    },

    # ── Links ────────────────────────────────────────────────────────────
    {
        # WCAG 2.4.4 und BITV 9.2.4.4 urteilen hier bewusst unterschiedlich:
        # „hier klicken" ist für WCAG ein Verstoß (generischer Linktext ohne
        # Kontext-Rückgriff), für BITV dagegen zulässig, wenn der Kontext den
        # Zweck benennt (binär: bestanden/nicht bestanden). Deshalb getrennte
        # Seiten je Testsystem statt einer zusammengefassten.
        "slug": "linktext",
        "kategorie": "Links",
        "titel": "Aussagekräftige Linktexte (WCAG)",
        "beschreibung": "WCAG 2.4.4: Generische Linktexte („hier klicken“, „mehr“) sind ein Verstoß, unabhängig vom Kontext.",
        "test_ids": ["WCAG_2_4_4_LINK_TEXT"],
        "positiv_html": _beispiel("positiv",
            '<p>Unsere <a href="/index.html">Preise ansehen</a>.</p>',
            "Aussagekräftiger Linktext"),
        "negativ_html": _beispiel("negativ",
            '<p><a href="/index.html">hier klicken</a></p>',
            None),
    },
    {
        "slug": "linktext-bitv",
        "kategorie": "Links",
        "titel": "Aussagekräftige Linktexte (BITV)",
        "beschreibung": "BITV 9.2.4.4: Links brauchen einen Text bzw. Namen; generischer Kurztext ist mit Kontext-Ausnahme zulässig. Urteil ist binär (bestanden/nicht bestanden).",
        "test_ids": ["BITV_9_2_4_4_AUSSAGEKRAEFTIGE_LINKTEXTE"],
        "positiv_html": _beispiel("positiv",
            '<p>Weitere Details im <a href="/index.html">Leitfaden zur Bedienung</a>.</p>',
            "Aussagekräftiger Linktext"),
        "negativ_html": _beispiel("negativ",
            '<p><a href="/index.html"></a></p>',
            "Link ohne Text"),
    },

    # ── Formulare ────────────────────────────────────────────────────────
    {
        "slug": "formular-label-programmatisch",
        "kategorie": "Formulare",
        "titel": "Programmatisch ermittelbare Formular-Labels",
        "beschreibung": "Eingabefelder brauchen ein programmatisch ermittelbares Label (label/aria-label/title).",
        "test_ids": ["WCAG_1_3_1_FORM_LABEL", "BITV_9_1_3_1h_BESCHRIFTUNG_VON_FORMULARELEMENTEN_PROGRAMMATISCH_ERMITTELBAR"],
        "positiv_html": _beispiel("positiv",
            '<label for="n">Nachricht</label><input type="text" id="n" name="nachricht">',
            "Feld mit Label"),
        "negativ_html": _beispiel("negativ",
            '<input type="text" name="nachricht" placeholder="Ihre Nachricht">',
            "Feld ohne programmatisches Label"),
    },
    {
        "slug": "formular-label-sichtbar",
        "kategorie": "Formulare",
        "titel": "Sichtbare Formular-Beschriftungen",
        "beschreibung": "Eingabefelder brauchen eine sichtbare Beschriftung — ein nur unsichtbares aria-label reicht nicht.",
        "test_ids": ["WCAG_3_3_2_LABELS"],
        "positiv_html": _beispiel("positiv",
            '<label for="n">Nachricht</label><input type="text" id="n" name="nachricht">',
            "Sichtbares Label"),
        "negativ_html": _beispiel("negativ",
            '<input type="text" name="nachricht" aria-label="Nachricht">',
            "Nur unsichtbares Label"),
    },
    {
        "slug": "formular-label-reihenfolge",
        "kategorie": "Formulare",
        "titel": "Beschriftung vor dem Formularfeld",
        "beschreibung": "Die sichtbare Beschriftung muss vor bzw. über dem Feld stehen.",
        "test_ids": ["BITV_9_3_3_2_BESCHRIFTUNGEN_VON_FORMULARELEMENTEN_VORHANDEN"],
        "positiv_html": _beispiel("positiv",
            '<label for="n">Nachricht</label><input type="text" id="n" name="nachricht">',
            "Label vor dem Feld"),
        "negativ_html": _beispiel("negativ",
            '<input type="text" id="n" name="nachricht"><label for="n">Nachricht</label>',
            "Label nach dem Feld"),
    },
    {
        "slug": "autocomplete",
        "kategorie": "Formulare",
        "titel": "Autocomplete-Attribute für Nutzerdaten",
        "beschreibung": "Felder für bekannte Nutzerdaten (E-Mail, Name, …) brauchen ein passendes autocomplete-Attribut.",
        "test_ids": ["WCAG_1_3_5_AUTOCOMPLETE", "BITV_9_1_3_5_EINGABEFELDER_ZU_NUTZERDATEN_VERMITTELN_DEN_ZWECK"],
        "positiv_html": _beispiel("positiv",
            # Label bewusst „E-Mail" statt „E-Mail-Adresse": das Substring-Keyword
            # „adresse" des street-address-Mappings würde sonst fälschlich
            # autocomplete="street-address" erwarten (False-Positive).
            '<label for="em">E-Mail</label><input type="email" id="em" name="email" autocomplete="email">',
            "Feld mit autocomplete"),
        "negativ_html": _beispiel("negativ",
            '<label for="em">E-Mail</label><input type="email" id="em" name="email">',
            "Feld ohne autocomplete"),
    },

    # ── Tabellen & Listen ────────────────────────────────────────────────
    {
        "slug": "tabellen-kopfzellen",
        "kategorie": "Tabellen & Listen",
        "titel": "Tabellen mit Kopfzellen",
        "beschreibung": "Datentabellen brauchen <th>-Kopfzellen.",
        "test_ids": ["WCAG_1_3_1_SR_TABLE_HEADERS", "BITV_9_1_3_1e_DATENTABELLEN_RICHTIG_AUFGEBAUT"],
        "positiv_html": _beispiel("positiv",
            '<div class="tabelle-wrap"><table><tr><th scope="col">Jahr</th><th scope="col">Umsatz</th></tr>'
            '<tr><td>2026</td><td>120</td></tr><tr><td>2027</td><td>150</td></tr></table></div>',
            "Tabelle mit Kopfzellen"),
        "negativ_html": _beispiel("negativ",
            '<div class="tabelle-wrap"><table><caption>Jahresumsätze</caption>'
            '<tr><td>2026</td><td>120</td></tr><tr><td>2027</td><td>150</td></tr></table></div>',
            "Datentabelle ohne Kopfzellen"),
    },
    {
        "slug": "tabellen-zellen-zuordnung",
        "kategorie": "Tabellen & Listen",
        "titel": "Zuordnung von Tabellenzellen",
        "beschreibung": "Komplexe Tabellen (colspan/rowspan) brauchen scope- oder id/headers-Zuordnungen.",
        "test_ids": ["BITV_9_1_3_1f_ZUORDNUNG_VON_TABELLENZELLEN"],
        "positiv_html": _beispiel("positiv",
            '<div class="tabelle-wrap"><table><caption>Umsätze nach Jahr</caption>'
            '<tr><th colspan="2" scope="colgroup">Jahr</th></tr>'
            '<tr><td>2026</td><td>120</td></tr><tr><td>2027</td><td>150</td></tr></table></div>',
            "Komplexe Tabelle mit Zuordnung"),
        "negativ_html": _beispiel("negativ",
            '<div class="tabelle-wrap"><table><caption>Umsätze nach Jahr</caption>'
            '<tr><th colspan="2">Jahr</th></tr>'
            '<tr><td>2026</td><td>120</td></tr><tr><td>2027</td><td>150</td></tr></table></div>',
            "Komplexe Tabelle ohne Zuordnung"),
    },
    {
        "slug": "listen",
        "kategorie": "Tabellen & Listen",
        "titel": "Listen mit Einträgen",
        "beschreibung": "Listenelemente (ul/ol/dl) dürfen nicht leer sein oder nur leere Einträge enthalten.",
        "test_ids": ["WCAG_1_3_1_SR_EMPTY_LIST", "BITV_9_1_3_1b_HTML_STRUKTURELEMENTE_FUER_LISTEN"],
        "positiv_html": _beispiel("positiv",
            '<ul><li>Erster Punkt</li><li>Zweiter Punkt</li></ul>',
            "Liste mit Einträgen"),
        "negativ_html": _beispiel("negativ",
            '<ul></ul>',
            "Leere Liste"),
    },

    # ── Struktur & Navigation ────────────────────────────────────────────
    {
        "slug": "einziges-main",
        "kategorie": "Struktur & Navigation",
        "titel": "Genau eine main-Landmarke",
        "beschreibung": "Eine Seite darf nur ein sichtbares main-Element (bzw. role=main) enthalten.",
        "test_ids": ["WCAG_1_3_1_LANDMARK_MAIN"],
        "extras_negativ": {"show_main": False},
        "positiv_html": _beispiel("positiv",
            '<p>Diese Seite hat genau ein <code>main</code>-Element.</p>',
            "Genau ein Hauptbereich"),
        "negativ_html": (
            '<main id="main"><h2>Erster Hauptbereich</h2><p>Inhalt des ersten Hauptbereichs.</p></main>\n'
            '<main><h2>Zweiter Hauptbereich</h2><p>Inhalt des zweiten Hauptbereichs.</p></main>'
        ),
    },
    {
        "slug": "skip-link",
        "kategorie": "Struktur & Navigation",
        "titel": "Mechanismus zum Überspringen von Blöcken",
        "beschreibung": "Wiederkehrende Blöcke müssen überspringbar sein (main-/nav-Landmarke oder Sprunglink).",
        "test_ids": ["WCAG_2_4_1_SKIP_LINKS", "BITV_9_2_4_1_BEREICHE_UEBERSPRINGBAR"],
        "extras_negativ": {"show_main": False, "show_skip": False, "show_nav": False},
        "positiv_html": _beispiel("positiv",
            '<p>Diese Seite hat eine <code>main</code>-Landmarke und einen Sprunglink.</p>',
            "Hauptbereich mit Sprunglink"),
        "negativ_html": _beispiel("negativ",
            '<h2>Inhalt ohne Bypass</h2>'
            '<p>Diese Seite hat weder <code>main</code> noch Navigation noch Sprunglink.</p>',
            "Kein Bypass-Mechanismus"),
    },
    {
        "slug": "navigation-benennung",
        "kategorie": "Struktur & Navigation",
        "titel": "Unterscheidbare Navigationsbereiche",
        "beschreibung": "Mehrere Navigationsbereiche brauchen aria-label/aria-labelledby zur Unterscheidung.",
        "test_ids": ["BITV_9_2_4_1_BEREICHE_UEBERSPRINGBAR"],
        "positiv_html": _beispiel("positiv",
            '<nav aria-label="Footer-Navigation"><a href="/index.html">Impressum</a></nav>',
            "Navigationsbereiche mit Namen"),
        "negativ_html": _beispiele(
            _beispiel("negativ", '<nav><a href="/index.html">Hauptmenü</a></nav>', "Erste Navigation"),
            _beispiel("negativ", '<nav><a href="/index.html">Untermenü</a></nav>', "Zweite Navigation"),
        ),
    },
    {
        "slug": "inhalt-gegliedert",
        "kategorie": "Struktur & Navigation",
        "titel": "Gegliederter Inhalt",
        "beschreibung": "Textabsätze mit p, keine doppelten <br>, keine Leerzeichen-Ketten, keine Zeichen-Trennlinien statt <hr>.",
        "test_ids": ["BITV_9_1_3_1d_INHALT_GEGLIEDERT"],
        "positiv_html": _beispiel("positiv",
            '<p>Ein ordentlicher Absatz.</p><hr><p>Ein weiterer Absatz.</p>',
            "Gegliederter Inhalt"),
        "negativ_html": _beispiele(
            _beispiel("negativ", '<p>Zeile eins<br><br>Zeile drei als neuer Absatz</p>', "Doppelte Zeilenumbrüche"),
            _beispiel("negativ", '<p>Spalte eins&nbsp;&nbsp;Spalte zwei</p>', "Leerzeichen-Kette"),
            _beispiel("negativ", '<p>---</p>', "Trennlinie aus Zeichen"),
        ),
    },

    # ── Sprache ──────────────────────────────────────────────────────────
    {
        "slug": "hauptsprache",
        "kategorie": "Sprache",
        "titel": "Hauptsprache der Seite",
        "beschreibung": "Die Sprache der Seite muss über ein gültiges BCP-47-lang-Attribut deklariert sein.",
        "test_ids": ["WCAG_3_1_1_LANG", "BITV_9_3_1_1_HAUPTSPRACHE_ANGEGEBEN"],
        "extras_negativ": {"lang": "englisch"},
        "positiv_html": _beispiel("positiv",
            '<p>Diese Seite deklariert gültig <code>lang="de"</code>.</p>',
            "Gültige Sprachangabe"),
        "negativ_html": _beispiel("negativ",
            '<p>Diese Seite deklariert eine ungültige Sprachangabe.</p>',
            "Ungültige Sprachangabe"),
    },
    {
        "slug": "sprachwechsel",
        "kategorie": "Sprache",
        "titel": "Sprachwechsel im Text",
        "beschreibung": "Fremdsprachige Abschnitte brauchen ein gültiges lang-Attribut mit dem richtigen Sprachkürzel.",
        "test_ids": ["WCAG_3_1_2_LANG_PARTS", "BITV_9_3_1_2_ANDERSSPRACHIGE_WOERTER_UND_ABSCHNITTE_AUSGEZEICHNET"],
        "positiv_html": _beispiel("positiv",
            '<p>Ein fremdsprachiger Einschub ist ausgezeichnet: <span lang="fr">Bonjour à tous</span>.</p>',
            "Gültiger Sprachwechsel"),
        "negativ_html": _beispiel("negativ",
            '<p>Ein fremdsprachiger Einschub ist nicht auswertbar: <span lang="englisch">Bonjour à tous</span>.</p>',
            "Ungültiger Sprachwechsel"),
    },

    # ── Seitentitel ──────────────────────────────────────────────────────
    {
        "slug": "seiten-titel",
        "kategorie": "Seitentitel",
        "titel": "Seitentitel vorhanden",
        "beschreibung": "Jede Seite braucht ein nicht-leeres <title>-Element.",
        "test_ids": ["WCAG_2_4_2_TITLE"],
        "extras_positiv": {"title": "Kontakt | A11Y Test-Website"},
        "extras_negativ": {"title": ""},
        "positiv_html": _beispiel("positiv",
            '<p>Diese Seite hat einen aussagekräftigen Seitentitel.</p>',
            "Seitentitel vorhanden"),
        "negativ_html": _beispiel("negativ",
            '<p>Diese Seite hat keinen Seitentitel.</p>',
            "Fehlender Seitentitel"),
    },
    {
        "slug": "seiten-titel-sinnvoll",
        "kategorie": "Seitentitel",
        "titel": "Sinnvoller Seitentitel",
        "beschreibung": "Der Seitentitel darf nicht generisch (z. B. „Home“) oder nur Schmuckzeichen sein.",
        "test_ids": ["BITV_9_2_4_2_SINNVOLLE_DOKUMENTTITEL"],
        "extras_positiv": {"title": "Datenschutzerklärung"},
        "extras_negativ": {"title": "Home"},
        "positiv_html": _beispiel("positiv",
            '<p>Diese Seite hat einen sinnvollen Seitentitel.</p>',
            "Sinnvoller Seitentitel"),
        "negativ_html": _beispiel("negativ",
            '<p>Diese Seite hat einen nichtssagenden Seitentitel.</p>',
            "Generischer Seitentitel"),
    },

    # ── ARIA & Bedienbarkeit ─────────────────────────────────────────────
    {
        "slug": "button-name",
        "kategorie": "ARIA & Bedienbarkeit",
        "titel": "Zugänglicher Name für Buttons",
        "beschreibung": "Jeder Button braucht einen zugänglichen Namen (Text, alt, aria-label o. Ä.).",
        "test_ids": ["WCAG_4_1_2_BUTTON_NAME"],
        "positiv_html": _beispiele(
            _beispiel("positiv", '<button type="button">Senden</button>', "Button mit Text"),
            _beispiel("positiv", '<button type="button" aria-label="Schließen">×</button>', "Button mit aria-label"),
        ),
        "negativ_html": _beispiel("negativ",
            '<button type="button"></button>',
            "Button ohne Namen"),
    },
    {
        "slug": "aria-name-missing",
        "kategorie": "ARIA & Bedienbarkeit",
        "titel": "Zugänglicher Name für interaktive Elemente",
        "beschreibung": "Interaktive ARIA-Elemente (z. B. role=checkbox) brauchen einen zugänglichen Namen.",
        "test_ids": ["WCAG_4_1_2_ARIA_LABEL_MISSING"],
        "positiv_html": _beispiel("positiv",
            '<div role="checkbox" tabindex="0" aria-checked="false" aria-label="Newsletter abonnieren">Newsletter abonnieren</div>',
            "Interaktives Element mit Namen"),
        "negativ_html": _beispiel("negativ",
            '<div role="checkbox" tabindex="0" aria-checked="false"></div>',
            "Interaktives Element ohne Namen"),
    },
    {
        "slug": "dialog-name",
        "kategorie": "ARIA & Bedienbarkeit",
        "titel": "Name für Dialoge",
        "beschreibung": "role=\"dialog\" braucht aria-label oder aria-labelledby.",
        "test_ids": ["WCAG_4_1_2_DIALOG_LABEL"],
        "positiv_html": _beispiel("positiv",
            '<div role="dialog" aria-label="Löschen bestätigen"><p>Möchten Sie wirklich löschen?</p></div>',
            "Dialog mit Namen"),
        "negativ_html": _beispiel("negativ",
            '<div role="dialog"><p>Möchten Sie wirklich löschen?</p></div>',
            "Dialog ohne Namen"),
    },
    {
        "slug": "invalid-role",
        "kategorie": "ARIA & Bedienbarkeit",
        "titel": "Gültige ARIA-Rollen",
        "beschreibung": "role-Attribute dürfen nur bekannte ARIA-Rollen verwenden.",
        "test_ids": ["WCAG_4_1_2_INVALID_ROLE"],
        "positiv_html": _beispiel("positiv",
            '<div role="status" aria-live="polite">Änderungen gespeichert</div>',
            "Gültige ARIA-Rolle"),
        "negativ_html": _beispiel("negativ",
            '<div role="quatsch-rolle">Beispiel</div>',
            "Ungültige ARIA-Rolle"),
    },
    {
        "slug": "aria-hidden-wert",
        "kategorie": "ARIA & Bedienbarkeit",
        "titel": "Gültiger aria-hidden-Wert",
        "beschreibung": "aria-hidden darf nur \"true\" oder \"false\" sein.",
        "test_ids": ["WCAG_4_1_2_ARIA_HIDDEN"],
        "positiv_html": _beispiel("positiv",
            '<div aria-hidden="true">Verborgener Hilfetext.</div>',
            "Gültiger aria-hidden-Wert"),
        "negativ_html": _beispiel("negativ",
            '<div aria-hidden="yes">Undeutlich verborgener Bereich.</div>',
            "Ungültiger aria-hidden-Wert"),
    },
    {
        "slug": "aria-expanded-wert",
        "kategorie": "ARIA & Bedienbarkeit",
        "titel": "Gültiger aria-expanded-Wert",
        "beschreibung": "aria-expanded darf nur \"true\" oder \"false\" sein.",
        "test_ids": ["WCAG_4_1_2_ARIA_EXPANDED"],
        "positiv_html": _beispiel("positiv",
            '<button type="button" aria-expanded="false">Menü</button>',
            "Gültiger aria-expanded-Wert"),
        "negativ_html": _beispiel("negativ",
            '<button type="button" aria-expanded="vielleicht">Menü</button>',
            "Ungültiger aria-expanded-Wert"),
    },
    {
        "slug": "statusmeldung-aria-live",
        "kategorie": "ARIA & Bedienbarkeit",
        "titel": "Gültige Live-Regionen",
        "beschreibung": "aria-live darf nur \"off\", \"polite\" oder \"assertive\" sein.",
        "test_ids": ["WCAG_4_1_3_ARIA_LIVE", "BITV_9_4_1_3_STATUSMELDUNGEN_PROGRAMMATISCH_VERFUEGBAR"],
        "positiv_html": _beispiel("positiv",
            '<div aria-live="polite">Nachricht gesendet</div>',
            "Gültige Live-Region"),
        "negativ_html": _beispiel("negativ",
            '<div aria-live="urgent">Achtung: neue Nachricht</div>',
            "Ungültiger aria-live-Wert"),
    },
    {
        "slug": "name-rolle-wert",
        "kategorie": "ARIA & Bedienbarkeit",
        "titel": "Name, Rolle und Wert verfügbar",
        "beschreibung": "Bedienelemente brauchen Rolle und Namen; Elemente mit Event-Handler ohne Rolle sind unzulässig (F59).",
        "test_ids": ["BITV_9_4_1_2_NAME_ROLLE_WERT_VERFUEGBAR"],
        "positiv_html": _beispiele(
            _beispiel("positiv", '<a href="/index.html">Funktionierender Link</a>', "Link mit href"),
            _beispiel("positiv",
                '<span role="button" tabindex="0" onclick="go()" aria-label="Aktion">Aktion</span>',
                "Bedienelement mit Rolle"),
        ),
        "negativ_html": _beispiele(
            _beispiel("negativ", '<a>Verwaister Link</a>', "Link ohne href und ohne Rolle"),
            _beispiel("negativ",
                '<span onclick="go()" tabindex="0">Klickbereich</span>',
                "Bedienelement ohne Rolle (F59)"),
        ),
    },

    # ── Zeitlimits ───────────────────────────────────────────────────────
    {
        "slug": "zeitlimit-refresh",
        "kategorie": "Zeitlimits",
        "titel": "Anpassbare Zeitbegrenzung (Meta-Refresh)",
        "beschreibung": "Ein Meta-Refresh mit Zeitbegrenzung (<meta http-equiv=refresh content=\"30\">) ist unzulässig.",
        "test_ids": ["WCAG_2_2_1_META_REFRESH", "BITV_9_2_2_1_ZEITBEGRENZUNGEN_ANPASSBAR"],
        "extras_negativ": {"head": '<meta http-equiv="refresh" content="30">'},
        "positiv_html": _beispiel("positiv",
            '<p>Diese Seite enthält keinen Meta-Refresh.</p>',
            "Keine Zeitbegrenzung"),
        "negativ_html": _beispiel("negativ",
            '<p>Diese Seite lädt sich nach 30 Sekunden neu.</p>',
            "Meta-Refresh mit Zeitbegrenzung"),
    },

    # ── Responsive & Viewport ────────────────────────────────────────────
    {
        "slug": "viewport-vorhanden",
        "kategorie": "Responsive & Viewport",
        "titel": "Viewport-Meta-Tag vorhanden",
        "beschreibung": "Mobile Seiten brauchen <meta name=\"viewport\"> für die korrekte Darstellung bei 320 px.",
        "test_ids": ["WCAG_1_4_10_VIEWPORT_MISSING", "BITV_9_1_4_10_INHALTE_BRECHEN_UM"],
        "extras_negativ": {"viewport": None},
        "positiv_html": _beispiel("positiv",
            '<p>Diese Seite hat ein gültiges viewport-Meta-Tag.</p>',
            "Viewport-Meta vorhanden"),
        "negativ_html": _beispiel("negativ",
            '<p>Diese Seite hat kein viewport-Meta-Tag.</p>',
            "Viewport-Meta fehlt"),
    },
    {
        "slug": "viewport-zoom",
        "kategorie": "Responsive & Viewport",
        "titel": "Zoomen nicht sperren",
        "beschreibung": "user-scalable=no oder maximum-scale ≤ 1 im viewport-Meta ist unzulässig.",
        "test_ids": ["WCAG_1_4_10_VIEWPORT_ZOOM", "BITV_9_1_4_10_INHALTE_BRECHEN_UM"],
        "extras_negativ": {"viewport": "width=device-width, initial-scale=1, user-scalable=no"},
        "positiv_html": _beispiel("positiv",
            '<p>Diese Seite erlaubt das Zoomen im Browser.</p>',
            "Zoom erlaubt"),
        "negativ_html": _beispiel("negativ",
            '<p>Diese Seite sperrt den Zoom.</p>',
            "Zoom gesperrt"),
    },
    {
        "slug": "reflow-320",
        "kategorie": "Responsive & Viewport",
        "titel": "Inhalt bricht bei 320 px um",
        "beschreibung": "Inhalt darf bei 320 px nicht horizontal überlaufen (keine festen Breiten).",
        "test_ids": ["WCAG_1_4_10_REFLOW", "BITV_9_1_4_10_INHALTE_BRECHEN_UM"],
        "positiv_html": _beispiel("positiv",
            '<div style="max-width:100%">Responsiver Inhalt, der bei 320&nbsp;px umbricht.</div>',
            "Responsiver Inhalt"),
        "negativ_html": _beispiel("negativ",
            '<div style="width:600px;background:#eef2f7;padding:1rem">Fester 600&nbsp;px breiter Block.</div>',
            "Fest breiter Inhalt"),
    },
    {
        "slug": "text-200-prozent",
        "kategorie": "Responsive & Viewport",
        "titel": "Text bei 200 % Zoom lesbar",
        "beschreibung": "Bei 200 % Zoom (bzw. halbierter Viewport-Breite) darf kein Text abgeschnitten werden.",
        "test_ids": ["WCAG_1_4_4_RESIZE", "BITV_9_1_4_4_TEXT_AUF_200_VERGROESSERBAR"],
        "positiv_html": _beispiel("positiv",
            '<p>Normal umbrechender Text, der bei jeder Zoomstufe sauber in die verfügbare Breite passt. '
            'Zeilenumbrüche erfolgen automatisch und der Text bleibt lesbar, ohne dass horizontal gescrollt werden muss.</p>',
            "Umbrechender Text"),
        "negativ_html": _beispiel("negativ",
            '<p style="white-space:nowrap">Diese Zeile darf nicht umbrechen. Sie ist absichtlich sehr lang, '
            'damit sie bei halbierter oder vergrößerter Ansicht über den sichtbaren Bereich hinausragt und der '
            'Resize-Check einen Befund melden kann. Lorem ipsum dolor sit amet, consectetur adipiscing elit, '
            'sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>',
            "Nicht umbrechender Text"),
    },
    {
        "slug": "textabstaende",
        "kategorie": "Responsive & Viewport",
        "titel": "Anpassbare Textabstände",
        "beschreibung": "Text darf bei größeren Zeichen- und Zeilenabständen nicht abgeschnitten oder überlappend werden.",
        "test_ids": ["WCAG_1_4_12_TEXT_SPACING", "BITV_9_1_4_12_TEXTABSTAENDE_ANPASSBAR"],
        "positiv_html": _beispiel("positiv",
            '<p>Normaler Text ohne feste Breite und ohne Clip-Eigenschaften. Er bricht um und bleibt auch bei '
            'größeren Zeichenabständen vollständig sichtbar.</p>',
            "Text ohne Clipping"),
        "negativ_html": _beispiel("negativ",
            '<p style="width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
            'Dieser Text wird bei größeren Abständen hart abgeschnitten statt umzubrechen — sehr langer Satz '
            'mit vielen Wörtern.</p>',
            "Text mit Clipping"),
    },

    # ── Fokus & Tastatur (feuern nur > 1160 px → im Scan bei 1920) ───────
    {
        "slug": "fokus-indikator",
        "kategorie": "Fokus & Tastatur",
        "titel": "Sichtbarer Fokus-Indikator",
        "beschreibung": "Der Tastaturfokus muss durch eine sichtbare Änderung erkennbar sein.",
        "test_ids": ["WCAG_2_4_7_FOCUS_INDICATOR", "BITV_9_2_4_7_AKTUELLE_POSITION_DES_FOKUS_DEUTLICH"],
        "extras_positiv": {
            "style": "button.fokus-sichtbar:focus, button.fokus-sichtbar:focus-visible { outline: 2px solid #005fcc; outline-offset: 2px; }",
        },
        "extras_negativ": {
            "style": "button.ohne-indikator:focus, button.ohne-indikator:focus-visible { outline: none; box-shadow: none; }",
        },
        "positiv_html": _beispiel("positiv",
            '<p><button type="button" class="fokus-sichtbar">Menü öffnen</button></p>',
            "Sichtbarer Fokus-Indikator"),
        "negativ_html": _beispiel("negativ",
            '<p><button type="button" class="ohne-indikator">Menü öffnen</button></p>',
            "Kein Fokus-Indikator"),
    },
    {
        "slug": "verstecktes-fokuselement",
        "kategorie": "Fokus & Tastatur",
        "titel": "Kein verstecktes fokussierbares Element",
        "beschreibung": "Fokussierbare Elemente müssen sichtbar sein (keine Null-Größe, kein opacity:0).",
        "test_ids": ["WCAG_2_4_7_HIDDEN_FOCUSABLE"],
        "positiv_html": _beispiel("positiv",
            '<p><a href="#a">Erster Link</a> · <a href="#b">Zweiter Link</a></p>',
            "Alle Fokuselemente sichtbar"),
        "negativ_html": _beispiel("negativ",
            '<p><a href="#a">Sichtbarer Link</a></p>'
            '<p><a href="#" tabindex="0" style="display:block;width:0;height:0;overflow:hidden;font-size:0">'
            'Verstecktes Ziel</a></p>',
            "Unsichtbares, aber fokussierbares Element"),
    },
    {
        "slug": "tastaturfalle",
        "kategorie": "Fokus & Tastatur",
        "titel": "Keine Tastaturfalle",
        "beschreibung": "Der Tastaturfokus darf sich nicht in einem Element verfangen (kein Tab-PreventDefault).",
        "test_ids": ["WCAG_2_1_2_KEYBOARD_TRAP", "BITV_9_2_1_2_KEINE_TASTATURFALLE"],
        "positiv_html": _beispiel("positiv",
            '<p><a href="#a">Link A</a> · <a href="#b">Link B</a> · <a href="#c">Link C</a></p>',
            "Tab-Reihenfolge ohne Falle"),
        "negativ_html": _beispiel("negativ",
            '<p>Der dritte Fokusstopp fängt den Tabulator ein.</p>\n'
            '<p><a href="#a" id="a">Link A</a> · '
            '<a href="#" id="falle" class="falle" style="display:inline-block" '
            'onkeydown="if(event.key===\'Tab\'){event.preventDefault();event.stopPropagation();}">Fokusfalle</a> · '
            '<a href="#b" id="b">Link B</a></p>',
            "Tastaturfalle"),
    },
    {
        "slug": "tabindex",
        "kategorie": "Fokus & Tastatur",
        "titel": "Kein positiver tabindex",
        "beschreibung": "Positive tabindex-Werte (tabindex=\"1\") stören die logische Tab-Reihenfolge.",
        "test_ids": ["WCAG_2_4_3_TABINDEX", "BITV_9_2_4_3_SCHLUESSIGE_REIHENFOLGE_BEI_DER_TASTATURBEDIENUNG"],
        "positiv_html": _beispiel("positiv",
            '<p><button type="button">Normaler Button</button></p>',
            "Ohne positiven tabindex"),
        "negativ_html": _beispiel("negativ",
            '<p><a href="#" tabindex="1">Erster Eintrag</a></p>',
            "Positiver tabindex"),
    },

    # ── Sonstige ─────────────────────────────────────────────────────────
    {
        "slug": "zielgroesse",
        "kategorie": "Sonstige",
        "titel": "Ausreichende Zielgröße",
        "beschreibung": "Bedienelemente sollten mindestens 44×44 px groß und nicht zu eng beieinander sein.",
        "test_ids": ["WCAG_2_5_5_TARGET_SIZE"],
        "positiv_html": _beispiel("positiv",
            '<div><button type="button" style="width:44px;height:44px;padding:0;margin:0;font-size:12px">OK</button></div>',
            "Ausreichende Zielgröße"),
        # Wichtig: Buttons NICHT in <p> einbetten — der 2.5.5-Check nimmt
        # (inline-block-)Ziele in Satzfluss-Eltern als „Inline-Ausnahme" aus.
        # <div> umgeht das, damit das Negativbeispiel wirklich feuert.
        "negativ_html": _beispiel("negativ",
            '<div><button type="button" style="width:30px;height:30px;padding:0;margin:0;font-size:12px">OK</button> '
            '<button type="button" style="width:30px;height:30px;padding:0;margin:0;font-size:12px">OK</button></div>',
            "Zu kleine Ziele"),
    },
    # ── BITV Batch 8: Stubs automatisiert ──────────────────────────────
    {
        "slug": "captcha-alternative",
        "kategorie": "Bilder & Grafiken",
        "titel": "Alternativen für CAPTCHAs",
        "beschreibung": "CAPTCHA-Grafiken brauchen einen Alternativtext mit Zweckbeschreibung und eine Alternative (z. B. Audio-Version).",
        "test_ids": ["BITV_9_1_1_1d_ALTERNATIVEN_FUER_CAPTCHAS"],
        "positiv_html": _beispiel("positiv",
            f'<form action="/senden">\n'
            f'  <label for="c">Sicherheitscode</label>\n'
            f'  <p><img id="captcha-bild" src="{DATA_GIF}" alt="CAPTCHA: Sicherheitscode ablesen und eingeben"></p>\n'
            f'  <p><a href="#audio-alternative">Zur Audio-Version des Codes</a></p>\n'
            f'  <input id="c" name="captcha" type="text">\n'
            f'</form>',
            "CAPTCHA mit Zweck-Alt-Text und Audio-Alternative"),
        "negativ_html": _beispiel("negativ",
            f'<form action="/senden">\n'
            f'  <label for="c">Sicherheitscode</label>\n'
            f'  <p><img id="captcha-bild" src="{DATA_GIF}"></p>\n'
            f'  <input id="c" name="captcha" type="text">\n'
            f'</form>',
            "CAPTCHA ohne Alternativtext und ohne Audio-Alternative"),
    },
    {
        "slug": "audio-volltext-bitv",
        "kategorie": "Medien & Video",
        "titel": "Alternativen für Audiodateien und stumme Videos",
        "beschreibung": "Reine Audio- und stumme Video-Inhalte brauchen eine Medienalternative (Transkript) in unmittelbarer Nähe.",
        "test_ids": ["BITV_9_1_2_1_ALTERNATIVEN_FUER_AUDIODATEIEN_UND_STUMME_VIDEOS"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                _audio_figure("a.mp3", controls=True, transcript=True),
                "Audio mit verlinktem Transkript"),
            _beispiel("positiv",
                _video_figure("v.mp4", controls=True, muted=True, transcript=True),
                "Stummes Video mit Transkript-Link"),
        ),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                _audio_figure("a.mp3", controls=True),
                "Audio ohne Transkript"),
            _beispiel("negativ",
                _video_figure("v.mp4", controls=True, muted=True),
                "Stummes Video ohne Alternative"),
        ),
    },
    {
        "slug": "video-ad-volltext",
        "kategorie": "Medien & Video",
        "titel": "Audiodeskription oder Volltext-Alternative für Videos",
        "beschreibung": "Tonbehaftete Videos brauchen eine Audiodeskriptions-Spur oder eine Volltext-Alternative.",
        "test_ids": ["BITV_9_1_2_3_AUDIODESKRIPTION_ODER_VOLLTEXT_ALTERNATIVE_FUER_VIDEOS"],
        "positiv_html": _beispiel("positiv",
            _video_figure("v.mp4", controls=True, descriptions=True),
            "Video mit Audiodeskriptions-Spur"),
        "negativ_html": _beispiel("negativ",
            _video_figure("v.mp4", controls=True),
            "Video ohne Audiodeskription und ohne Volltext"),
    },
    {
        "slug": "kontrast-grafik",
        "kategorie": "Kontrast & Farbe",
        "titel": "Kontraste von Grafiken und grafischen Bedienelementen",
        "beschreibung": "Bedienelemente, die nur über ihren Rahmen erkennbar sind, brauchen einen Rahmenkontrast von 3:1.",
        "test_ids": ["BITV_9_1_4_11_KONTRASTE_VON_GRAFIKEN_UND_GRAFISCHEN_BEDIENELEMENTEN_AUSREICHEND"],
        "positiv_html": _beispiel("positiv",
            '<p><button type="button" style="border: 2px solid #1a1a1a; background: #ffffff; padding: 6px 12px;">Senden</button></p>',
            "Rahmen mit ausreichendem Kontrast"),
        "negativ_html": _beispiel("negativ",
            '<p><button type="button" style="border: 2px solid #e3e3e3; background: #ffffff; padding: 6px 12px;">Senden</button></p>',
            "Rahmen mit zu geringem Kontrast"),
    },
    {
        "slug": "ohne-maus",
        "kategorie": "Fokus & Tastatur",
        "titel": "Ohne Maus nutzbar",
        "beschreibung": "Bedienelemente müssen per Tastatur erreichbar und aktivierbar sein — Maus-only-Handler auf nicht-fokussierbaren Elementen sind ein Verstoß.",
        "test_ids": ["BITV_9_2_1_1_OHNE_MAUS_NUTZBAR"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                '<p><button type="button" onclick="go()">Aktion</button></p>',
                "Native Schaltfläche mit onClick"),
            _beispiel("positiv",
                '<p><a href="/index.html" onclick="track()">Zur Startseite</a></p>',
                "Link mit onClick"),
        ),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<div onclick="go()" class="karte">Nur mit Maus klickbar</div>',
                "div mit onClick ohne Fokus"),
            _beispiel("negativ",
                '<p><span role="button" tabindex="0" onclick="go()">Tastatur-Aktivierung fehlt</span></p>',
                "tabindex-Element mit onClick ohne Key-Handler"),
        ),
    },
    {
        "slug": "tastatur-kurzbefehl",
        "kategorie": "Fokus & Tastatur",
        "titel": "Tastatur-Kurzbefehle abschaltbar oder anpassbar",
        "beschreibung": "Einzelzeichen-Kurzbefehle brauchen einen Modifikator oder eine Abschalt-/Anpassungsmöglichkeit.",
        "test_ids": ["BITV_9_2_1_4_TASTATUR_KURZBEFEHLE_ABSCHALTBAR_ODER_ANPASSBAR", "WCAG_2_1_4_CHAR_SHORTCUTS"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                '<p><input onkeydown="if (event.key === \'j\' && event.ctrlKey) jump()" placeholder="Suche"></p>',
                "Kurzbefehl mit Modifikator"),
            _beispiel("positiv",
                '<p><input onkeydown="if (event.key === \'Enter\') save()" placeholder="Suche"></p>',
                "Nur benannte Taste"),
        ),
        "negativ_html": _beispiel("negativ",
            '<p><input onkeydown="if (event.key === \'j\') jump()" placeholder="Suche"></p>',
            "Einzelzeichen-Kurzbefehl ohne Modifikator"),
    },
    {
        "slug": "bewegte-inhalte",
        "kategorie": "Sonstige",
        "titel": "Bewegte Inhalte abschaltbar",
        "beschreibung": "Laufende/blinkende Inhalte brauchen einen Abschalt- oder Pause-Mechanismus.",
        "test_ids": ["BITV_9_2_2_2_BEWEGTE_INHALTE_ABSCHALTBAR", "WCAG_2_2_2_ANIMATIONS"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                '<p><marquee>Laufschrift</marquee></p>\n'
                '<p><button type="button" onclick="pause()">Animation pausieren</button></p>',
                "Laufschrift mit Pause-Button"),
        ),
        "negativ_html": _beispiel("negativ",
            '<p><marquee>Laufschrift</marquee></p>',
            "Laufschrift ohne Abschalt-Mechanismus"),
    },
    {
        "slug": "label-in-name",
        "kategorie": "ARIA & Bedienbarkeit",
        "titel": "Sichtbare Beschriftung Teil des zugänglichen Namens",
        "beschreibung": "Die sichtbare Beschriftung eines Bedienelements muss im zugänglichen Namen enthalten sein.",
        "test_ids": ["BITV_9_2_5_3_SICHTBARE_BESCHRIFTUNG_TEIL_DES_ZUGAENGLICHEN_NAMENS", "WCAG_2_5_3_LABEL_IN_NAME"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                '<p><button type="button" aria-label="Senden">Senden</button></p>',
                "Button mit passendem aria-label"),
            _beispiel("positiv",
                '<p><button type="button" aria-label="Schließen">×</button></p>',
                "Icon-Button mit aria-label (Symbol kein Label)"),
            _beispiel("positiv",
                '<p><label for="fn">Vorname</label><input id="fn" type="text" aria-label="Vorname"></p>',
                "Eingabefeld mit passendem aria-label"),
        ),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<p><button type="button" aria-label="Absenden">Senden</button></p>',
                "Button: aria-label ohne sichtbaren Text"),
            _beispiel("negativ",
                '<p><label for="em">E-Mail</label><input id="em" type="email" aria-label="Mailadresse"></p>',
                "Eingabefeld: aria-label ohne sichtbare Beschriftung"),
        ),
    },
    {
        "slug": "html-syntax",
        "kategorie": "Sonstige",
        "titel": "Korrekte HTML-Syntax (W3C-Validator)",
        "beschreibung": "Valides HTML ohne doppelte IDs und fehlende schließende Tags (W3C-Validator; braucht Netz).",
        "test_ids": ["WCAG_4_1_1_HTML_ERROR", "WCAG_4_1_1_HTML_WARNING", "BITV_9_4_1_1_KORREKTE_SYNTAX"],
        "pytest": False,
        "positiv_html": _beispiel("positiv",
            '<p>Valides HTML ohne doppelte IDs und ohne fehlende schließende Tags.</p>',
            "Valides HTML"),
        "negativ_html": _beispiele(
            _beispiel("negativ", '<p id="doppelt">Erster Text.</p><p id="doppelt">Zweiter Text.</p>', "Doppelte ID"),
            _beispiel("negativ", '<div><span>Fehlendes schließendes Tag</div>', "Fehlendes schließendes Tag"),
        ),
    },
    {
        "slug": "zitat-struktur",
        "kategorie": "Struktur & Navigation",
        "titel": "HTML-Strukturelemente für Zitate",
        "beschreibung": "Eigenständige Zitate sollen mit blockquote/q ausgezeichnet sein — nicht nur visuell per Klasse oder Anführungszeichen.",
        "test_ids": ["BITV_9_1_3_1c_HTML_STRUKTURELEMENTE_FUER_ZITATE"],
        "positiv_html": _beispiel("positiv",
            '<blockquote><p>„Der Mensch ist frei geboren, und überall liegt er in Ketten.“ — Jean-Jacques Rousseau</p></blockquote>',
            "Zitat als blockquote"),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<div class="zitat"><p>„Ein Textabschnitt, der nur über eine CSS-Klasse als Zitat markiert wird, obwohl das dafür vorgesehene HTML-Element blockquote genutzt werden sollte.“</p></div>',
                "Zitat nur visuell markiert (Klasse)"),
            _beispiel("negativ",
                '<p>„Dieser Abschnitt ist nur typografisch durch Anführungszeichen als Zitat gekennzeichnet, ohne die passende HTML-Struktur blockquote.“</p>',
                "Zitat nur typografisch markiert"),
        ),
    },
    {
        "slug": "flackern",
        "kategorie": "Struktur & Navigation",
        "titel": "Verzicht auf Flackern",
        "beschreibung": "Inhalte blitzen nicht häufiger als dreimal pro Sekunde — keine blink-Elemente und keine text-decoration: blink.",
        "test_ids": ["BITV_9_2_3_1_VERZICHT_AUF_FLACKERN", "WCAG_2_3_1_THREE_FLASHES"],
        "positiv_html": _beispiel("positiv",
            '<p>Statischer Hinweistext ohne blinkende Elemente oder Flacker-Animationen.</p>',
            "Keine blinkenden Inhalte"),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<p><blink>Wichtig: Diese Meldung blinkt permanent.</blink></p>',
                "blink-Element"),
            _beispiel("negativ",
                '<p style="text-decoration: blink">Dieser Text blinkt über text-decoration.</p>',
                "text-decoration: blink"),
        ),
    },
    {
        "slug": "zugangswege",
        "kategorie": "Struktur & Navigation",
        "titel": "Alternative Zugangswege",
        "beschreibung": "Mindestens zwei unterschiedliche Zugangswege zu den Inhalten — z. B. Navigation, Suche oder Sitemap-Link.",
        "test_ids": ["BITV_9_2_4_5_ALTERNATIVE_ZUGANGSWEGE", "WCAG_2_4_5_MULTIPLE_WAYS"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                '<form role="search"><label for="suche">Suche</label>'
                '<input id="suche" name="suche" type="search"></form>',
                "Suche als zweiter Zugangsweg neben der Navigation"),
            _beispiel("positiv",
                '<p><a href="/index.html">Inhaltsübersicht</a></p>',
                "Sitemap-Link als weiterer Zugangsweg"),
        ),
        "negativ_html": _beispiel("negativ",
            '<p>Diese Seite bietet nur den einen Weg über die Fußzeile — '
            'keine Suche, keine Sitemap und keine Navigationsstruktur.</p>',
            "Kein zweiter Zugangsweg"),
        "extras_negativ": {"show_nav": False},
    },
    {
        "slug": "fokus-kontext",
        "kategorie": "Bedienbarkeit",
        "titel": "Keine unerwartete Kontextänderung bei Fokus",
        "beschreibung": "Beim Fokuserhalt (oder Laden der Seite) wird kein Fenster geöffnet, kein Formular abgeschickt und nicht navigiert.",
        "test_ids": ["BITV_9_3_2_1_KEINE_UNERWARTETE_KONTEXTAENDERUNG_BEI_FOKUS", "WCAG_3_2_1_ON_FOCUS"],
        "positiv_html": _beispiel("positiv",
            '<p><input type="text" onfocus="this.select()" aria-label="Eingabefeld"></p>',
            "onfocus mit harmloser Aktion"),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<p><button type="button" onfocus="window.open(\'/index.html\')">Hilfe anfordern</button></p>',
                "onfocus öffnet ein neues Fenster"),
            _beispiel("negativ",
                '<p><input type="text" onfocus="location.href=\'/index.html\'" aria-label="Eingabefeld"></p>',
                "onfocus navigiert zur Startseite"),
        ),
    },
    {
        "slug": "eingabe-kontext",
        "kategorie": "Bedienbarkeit",
        "titel": "Keine unerwartete Kontextänderung bei Eingabe",
        "beschreibung": "Formularfelder lösen bei Eingabe keine unerwartete Kontextänderung aus (kein Auto-Submit, keine Navigation).",
        "test_ids": ["BITV_9_3_2_2_KEINE_UNERWARTETE_KONTEXTAENDERUNG_BEI_EINGABE", "WCAG_3_2_2_ON_INPUT"],
        "positiv_html": _beispiel("positiv",
            '<form><label for="land">Land</label>'
            '<select id="land"><option>Deutschland</option><option>Österreich</option></select>'
            '<button type="submit">Senden</button></form>',
            "Auswahl ohne Auto-Submit"),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<form id="auto"><label for="stadt">Stadt</label>'
                '<select id="stadt" onchange="this.form.submit()">'
                '<option>Berlin</option><option>Hamburg</option></select></form>',
                "onchange schickt das Formular automatisch ab"),
            _beispiel("negativ",
                '<p><input type="text" onchange="location.href=\'/index.html\'" aria-label="Eingabefeld"></p>',
                "onchange navigiert zur Startseite"),
        ),
    },
    {
        "slug": "fehlererkennung",
        "kategorie": "Formulare",
        "titel": "Fehlererkennung",
        "beschreibung": "Fehler werden automatisch erkannt und beschrieben — auch wenn die native Validierung (novalidate) ausgeschaltet ist.",
        "test_ids": ["BITV_9_3_3_1_FEHLERERKENNUNG"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                '<form><label for="mail">E-Mail</label>'
                '<input type="email" id="mail" name="mail" required>'
                '<button type="submit">Senden</button></form>',
                "Native Validierung aktiv"),
            _beispiel("positiv",
                '<form novalidate><label for="name">Name</label>'
                '<input id="name" name="name" required aria-invalid="false">'
                '<button type="submit">Senden</button></form>',
                "novalidate mit aria-invalid-Mechanismus"),
        ),
        "negativ_html": _beispiel("negativ",
            '<form novalidate><label for="nachricht">Nachricht</label>'
            '<textarea id="nachricht" name="nachricht" required></textarea>'
            '<button type="submit">Senden</button></form>',
            "novalidate ohne Fehler-Anzeige-Mechanismus"),
    },
    {
        "slug": "erklaerung",
        "kategorie": "Struktur & Navigation",
        "titel": "Erklärung zur Barrierefreiheit",
        "beschreibung": "Die Seite verlinkt eine aktuelle Erklärung zur Barrierefreiheit (üblicherweise im Footer).",
        "test_ids": ["BITV_7_DECLARATION"],
        "positiv_html": _beispiel("positiv",
            '<p>Alle Seiten dieses Angebots verlinken im Footer die Erklärung zur Barrierefreiheit.</p>',
            "Erklärung im Footer verlinkt"),
        "negativ_html": _beispiel("negativ",
            '<p>Diese Seite bietet keine Erklärung zur Barrierefreiheit und verlinkt auch keine.</p>',
            "Keine verlinkte Erklärung"),
        # Titel ohne den Katalog-Begriff, sonst würde der BITV-7-Check die
        # Negativ-Seite als „selbst die Erklärung" ausnehmen.
        "extras_negativ": {"show_declaration": False,
                           "title": "Negativbeispiel ohne Link auf die Erklärung · A11Y Test-Website"},
    },
    {
        "slug": "layout-tabelle",
        "kategorie": "Struktur & Navigation",
        "titel": "Kein Strukturmarkup für Layouttabellen",
        "beschreibung": "Als Layout deklarierte Tabellen (role=presentation) dürfen kein Tabellenstruktur-Markup (th, caption, summary, scope) enthalten.",
        "test_ids": ["BITV_9_1_3_1g_KEIN_STRUKTURMARKUP_FUER_LAYOUTTABELLEN"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                '<table role="presentation"><tr><td class="layout-marke">L</td><td>Zweispaltiges Layout ohne Tabellensemantik.</td></tr></table>',
                "Layouttabelle ohne Strukturmarkup"),
            _beispiel("positiv",
                '<table><caption>Quartalsumsätze</caption><tr><th scope="col">Monat</th><th scope="col">Betrag</th></tr><tr><td>Januar</td><td>120 €</td></tr></table>',
                "Echte Datentabelle mit Strukturmarkup"),
        ),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<table role="presentation" summary="Layouttabelle"><tr><th>Spalte A</th><th>Spalte B</th></tr><tr><td>Text A</td><td>Text B</td></tr></table>',
                "role=presentation mit th und summary"),
            _beispiel("negativ",
                '<table role="none"><tr><td scope="col">Zelle mit scope-Attribut</td></tr></table>',
                "role=none mit scope-Attribut"),
        ),
    },
    {
        "slug": "sensorisch",
        "kategorie": "Verständlichkeit",
        "titel": "Ohne Bezug auf sensorische Merkmale nutzbar",
        "beschreibung": "Anweisungen nennen zusätzlich zu Farbe, Form oder Position einen unabhängigen Bezug (z. B. den Text einer Überschrift).",
        "test_ids": ["BITV_9_1_3_3_OHNE_BEZUG_AUF_SENSORISCHE_MERKMALE_NUTZBAR", "WCAG_1_3_3_SENSORY"],
        "positiv_html": _beispiel("positiv",
            '<p>Zum Fortfahren: Wählen Sie im Abschnitt „Weiterleitung“ die Option „Fortfahren“.</p>',
            "Anweisung ohne sensorische Merkmale"),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<p>Klicken Sie zum Fortfahren auf den roten Button.</p>',
                "Anweisung nur über Farbe"),
            _beispiel("negativ",
                '<p>Die Navigation befindet sich in der linken Spalte.</p>',
                "Anweisung nur über Position"),
        ),
    },
    {
        "slug": "tastatur-reihenfolge",
        "kategorie": "Bedienbarkeit",
        "titel": "Schlüssige Reihenfolge bei der Tastaturbedienung",
        "beschreibung": "Keine positiven tabindex-Werte, die die natürliche Fokus-Reihenfolge umstellen.",
        "test_ids": ["BITV_9_2_4_3_SCHLUESSIGE_REIHENFOLGE_BEI_DER_TASTATURBEDIENUNG"],
        "positiv_html": _beispiel("positiv",
            '<p><a href="/index.html">Startseite</a> · <a href="/index.html" tabindex="-1">Nur für Programm-Fokus</a></p>',
            "tabindex 0/-1 lassen die natürliche Reihenfolge bestehen"),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<p><a href="/index.html" tabindex="3">Startseite</a> steht im Quelltext vor dem Kontakt-Link.</p>',
                "Positives tabindex hebt die Dokumentreihenfolge auf"),
            _beispiel("negativ",
                '<p><input type="text" tabindex="7" aria-label="Suchfeld"></p>',
                "Positives tabindex an einem Eingabefeld"),
        ),
    },
    {
        "slug": "bewegung",
        "kategorie": "Bedienbarkeit",
        "titel": "Alternativen für Bewegungsaktivierung",
        "beschreibung": "Gerätebewegung (Shake/Neigen) löst keine Funktion aus, ohne dass eine alternative Bedienung vorhanden ist.",
        "test_ids": ["BITV_9_2_5_4_ALTERNATIVEN_FUER_BEWEGUNGSAKTIVIERUNG", "WCAG_2_5_4_MOTION"],
        "positiv_html": _beispiel("positiv",
            '<p>Diese Seite reagiert nicht auf Gerätebewegungen; alle Funktionen sind per Maus und Tastatur bedienbar.</p>',
            "Keine Bewegungsaktivierung"),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<p><button type="button" id="schuetten">Rundenliste neu laden</button></p>'
                '<script>window.addEventListener("deviceorientation", function (e) { '
                'document.getElementById("schuetten").click(); });</script>',
                "deviceorientation löst Funktion aus"),
            _beispiel("negativ",
                '<p><button type="button" onclick="startDeviceMotionTracking()">Tracking starten</button></p>',
                "Inline-Handler nutzt Bewegungs-API"),
        ),
    },
    {
        "slug": "fehlervermeidung",
        "kategorie": "Formulare",
        "titel": "Fehlervermeidung wird unterstützt",
        "beschreibung": "Transaktionsformulare (z. B. Bestellung, Zahlung) bieten vor dem Absenden einen Prüf-/Bestätigungs-Mechanismus.",
        "test_ids": ["BITV_9_3_3_4_FEHLERVERMEIDUNG_WIRD_UNTERSTUETZT", "WCAG_3_3_4_ERROR_PREVENTION"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                '<form><p><label for="iban">IBAN</label>'
                '<input id="iban" name="iban" autocomplete="iban" required></p>'
                '<p><label><input type="checkbox" name="bestaetigung"> '
                'Ich habe meine Angaben geprüft und bestätige sie.</label></p>'
                '<button type="submit">Bestellung absenden</button></form>',
                "Bestätigungs-Kontrollkästchen"),
            _beispiel("positiv",
                '<form><p><label for="kontonummer">Kontonummer</label>'
                '<input id="kontonummer" name="kontonummer" required></p>'
                '<button type="submit" name="pruefen">Angaben prüfen</button></form>',
                "Prüf-Button vor dem Absenden"),
        ),
        "negativ_html": _beispiel("negativ",
            '<form><p><label for="iban">IBAN</label>'
            '<input id="iban" name="iban" required></p>'
            '<button type="submit">Bestellung absenden</button></form>',
            "Transaktion ohne Bestätigungs-/Prüf-Mechanismus"),
    },
    {
        "slug": "gebardensprache",
        "kategorie": "Barrierefreiheits-Angebote",
        "titel": "Gebärdensprach-Video auf der Startseite",
        "beschreibung": "Die wichtigsten Inhalte werden auch in Deutscher Gebärdensprache (DGS) als Video angeboten und von jeder Seite verlinkt.",
        "test_ids": ["BITV_4_SIGN_LANGUAGE", "WCAG_1_2_6_SIGN_LANGUAGE"],
        "positiv_html": _beispiel("positiv",
            '<p>Die wichtigsten Inhalte stehen zusätzlich als Gebärdensprach-Video zur Verfügung (Link im Footer).</p>'
            + _video_figure("v.mp4", controls=True, muted=True, transcript=True, caption="Gebärdensprach-Video"),
            "Gebärdensprach-Angebot verlinkt"),
        "negativ_html": _beispiel("negativ",
            '<p>Diese Seite bietet kein Gebärdensprach-Video an und verlinkt auch keines.</p>'
            + _video_figure("v.mp4", controls=True, muted=True, transcript=True, caption="Produktvideo"),
            "Kein verlinktes Gebärdensprach-Angebot"),
        "extras_negativ": {"show_sign_language": False,
                           "title": "Negativbeispiel ohne Video-Angebot für gehörlose Nutzer · A11Y Test-Website"},
    },
    {
        "slug": "leichte-sprache",
        "kategorie": "Barrierefreiheits-Angebote",
        "titel": "Leichte-Sprache-Angebot auf der Startseite",
        "beschreibung": "Die wichtigsten Inhalte werden auch in Leichter Sprache angeboten und von jeder Seite verlinkt.",
        "test_ids": ["BITV_4_EASY_LANGUAGE"],
        "positiv_html": _beispiel("positiv",
            '<p>Die wichtigsten Inhalte stehen zusätzlich in Leichter Sprache zur Verfügung (Link im Footer).</p>',
            "Leichte-Sprache-Angebot verlinkt"),
        "negativ_html": _beispiel("negativ",
            '<p>Diese Seite bietet keine Fassung in Leichter Sprache an und verlinkt auch keine.</p>',
            "Kein verlinktes Leichte-Sprache-Angebot"),
        "extras_negativ": {"show_easy_language": False,
                           "title": "Negativbeispiel ohne vereinfachtes Sprach-Angebot · A11Y Test-Website"},
    },
    {
        "slug": "ausrichtung",
        "kategorie": "Bedienbarkeit",
        "titel": "Keine Beschränkung der Bildschirmausrichtung",
        "beschreibung": "Die Bildschirmausrichtung wird nicht programmatisch gesperrt — Inhalte funktionieren im Hoch- und Querformat.",
        "test_ids": ["BITV_9_1_3_4_KEINE_BESCHRAENKUNG_DER_BILDSCHIRMAUSRICHTUNG", "WCAG_1_3_4_ORIENTATION"],
        "positiv_html": _beispiel("positiv",
            '<p>Die Seite passt sich jeder Bildschirmausrichtung an; es gibt keinen Orientierungs-Lock.</p>',
            "Kein Orientierungs-Lock"),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<script>if (screen.orientation) { screen.orientation.lock("portrait"); }</script>'
                '<p>Die Seite sperrt sich ins Hochformat.</p>',
                "screen.orientation.lock"),
            _beispiel("negativ",
                '<script>window.lockOrientation("landscape");</script>'
                '<p>Die Seite sperrt sich ins Querformat.</p>',
                "lockOrientation"),
        ),
    },
    {
        "slug": "gesten",
        "kategorie": "Bedienbarkeit",
        "titel": "Alternativen für komplexe Zeiger-Gesten",
        "beschreibung": "Funktionen, die über Wisch- oder Mehrpunkt-Gesten bedient werden, bieten eine einfache Zeigeralternative.",
        "test_ids": ["BITV_9_2_5_1_ALTERNATIVEN_FUER_KOMPLEXE_ZEIGER_GESTEN", "WCAG_2_5_1_POINTER_GESTURES"],
        "positiv_html": _beispiel("positiv",
            '<p><button type="button">Einfacher Klick genügt für alle Funktionen.</button></p>',
            "Nur einfache Zeigereingaben"),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<script>karte.addEventListener("touchmove", function (e) { '
                'if (e.touches.length > 1) { zoomKarte(); } });</script>'
                '<p>Zwei-Finger-Pinch zoomt die Karte.</p>',
                "Mehrpunkt-Geste (touches.length)"),
            _beispiel("negativ",
                '<script>var swiper = new Hammer(galerie);</script>'
                '<p>Wischgeste wechselt die Galerie-Bilder.</p>',
                "Gesten-Bibliothek (Hammer.js)"),
        ),
    },
    {
        "slug": "zeiger-abbruch",
        "kategorie": "Bedienbarkeit",
        "titel": "Zeigergesten-Eingaben können abgebrochen oder widerrufen werden",
        "beschreibung": "Aktionen werden nicht bereits beim Drücken eines Zeigers ausgelöst — das Loslassen (oder Widerrufen) bleibt möglich.",
        "test_ids": ["BITV_9_2_5_2_ZEIGERGESTEN_EINGABEN_KOENNEN_ABGEBROCHEN_ODER_WIDERRUFEN_WERDEN", "WCAG_2_5_2_POINTER_CANCEL"],
        "positiv_html": _beispiel("positiv",
            '<p><button type="button" onclick="window.location.href=\'/index.html\'">Zur Übersicht</button></p>',
            "Aktion erst beim Klick/Loslassen"),
        "negativ_html": _beispiele(
            _beispiel("negativ",
                '<form><p><button type="button" onmousedown="this.form.submit()">Sofort auslösen</button></p></form>',
                "onmousedown schickt das Formular ab"),
            _beispiel("negativ",
                '<div class="kachel" ontouchstart="location.href=\'/index.html\'">Zum Inhalt</div>',
                "ontouchstart navigiert sofort"),
        ),
    },
    {
        "slug": "hilfe-fehler",
        "kategorie": "Formulare",
        "titel": "Hilfe bei Fehlern",
        "beschreibung": "Fehlermeldungen sind verständlich und geben einen Hinweis, wie der Fehler zu korrigieren ist.",
        "test_ids": ["BITV_9_3_3_3_HILFE_BEI_FEHLERN", "WCAG_3_3_3_ERROR_SUGGESTION"],
        "positiv_html": _beispiele(
            _beispiel("positiv",
                '<form><p><label for="mail">E-Mail</label>'
                '<input id="mail" name="mail" type="email" aria-invalid="true" '
                'aria-describedby="hinweis-mail">'
                '<span id="hinweis-mail" class="fehler">Bitte geben Sie eine gültige '
                'E-Mail-Adresse ein (z. B. name@beispiel.de).</span></p></form>',
                "Fehlermeldung mit Beispiel"),
            _beispiel("positiv",
                '<form><p><label for="passwort">Passwort</label>'
                '<input id="passwort" name="passwort" type="password" aria-invalid="true" '
                'aria-describedby="hinweis-passwort">'
                '<span id="hinweis-passwort" class="fehler">Das Passwort muss mindestens '
                '8 Zeichen lang sein.</span></p></form>',
                "Fehlermeldung mit Mindestangabe"),
        ),
        "negativ_html": _beispiel("negativ",
            '<form><p><label for="mail">E-Mail</label>'
            '<input id="mail" name="mail" type="email" aria-invalid="true" '
            'aria-describedby="hinweis-mail">'
            '<span id="hinweis-mail" class="fehler">Eingabe ungültig.</span></p></form>',
            "Fehlermeldung ohne Korrektur-Hinweis"),
    },
]


if __name__ == "__main__":
    build()
