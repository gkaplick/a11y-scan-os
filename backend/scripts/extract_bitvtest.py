"""
bitvtest.de extrahieren — die 98 BITV-2.0-Web-Prüfschritte als strukturiertes
JSON lokal ablegen.

Quelle: https://bitvtest.de/pruefverfahren/bitv-20-web  (BIK BITV-Test,
offizielles Prüfverfahren zur BITV 2.0 / EN 301 549 für Web).

Vorgehen:
1. Index-Seite laden und alle Detail-Seiten-Slugs extrahieren.
2. Je Prüfschritt die Detail-Seite laden (polite Delay) und mit BeautifulSoup
   in Abschnitte zerlegen (Was wird geprüft / Warum / Wie / Quellen /
   Einordnung …).
3. Die „Einordnung nach WCAG 2.2"-Tabelle gezielt auslesen
   (Guideline / Success Criterion / Level / Techniques).
4. Je Test eine JSON-Datei nach ``<out>/<bitv_nummer>.json`` schreiben.

Lauf (im api-Container, dort sind bs4/requests installiert; docs/ ist als
``/app/docs`` gemountet):

    MSYS_NO_PATHCONV=1 docker compose run --rm \
      -v "G:/Meine Projekte/a11y-scanner/backend:/app" \
      api python /app/scripts/extract_bitvtest.py [--slug ...] [--out ...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://bitvtest.de"
INDEX_PATH = "/pruefverfahren/bitv-20-web"
DETAIL_PREFIX = "/pruefschritt/bitv-20-web/"
DEFAULT_OUT = Path("/app/docs/bitvtest")
DELAY_S = 0.4  # höflich crawlen

_SLUG_RE = re.compile(r'href="(/pruefschritt/bitv-20-web/[^"]+)"')


# -------------------------------------------------------------------- Download

def fetch(url: str, session: requests.Session) -> str:
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def fetch_slugs(session: requests.Session) -> list[str]:
    html = fetch(BASE + INDEX_PATH, session)
    slugs = sorted(set(_SLUG_RE.findall(html)))
    if not slugs:
        raise RuntimeError("Keine Prüfschritt-Links in der Index-Seite gefunden.")
    return slugs


# ------------------------------------------------------------- HTML → Markdown

# Elemente, die als Block behandelt werden (bewirken Zeilenumbruch).
_BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
               "ul", "ol", "li", "table", "tr", "br", "blockquote", "dl",
               "dt", "dd", "pre", "figure", "figcaption", "hr"}


def _inner_text(el) -> str:
    """Nur den sichtbaren Text des Elements (ohne Unter-Elemente) liefern."""
    parts = []
    for node in el.children:
        if getattr(node, "name", None) is None:  # NavigableString
            parts.append(str(node))
    return "".join(parts).strip()


def _node_to_markdown(el, depth: int = 0) -> str:
    """Element-Baum nach Markdown konvertieren (auf die genutzten Tags fokussiert)."""
    name = getattr(el, "name", None)
    if name is None:  # reiner Textknoten
        text = str(el).strip()
        return text

    if name in ("script", "style", "svg", "button", "noscript"):
        return ""

    if name == "br":
        return "  \n"

    children = "".join(_node_to_markdown(c, depth + 1) for c in el.children)

    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(name[1])
        # get_text() statt _inner_text(), damit Inline-<code> (z. B. title-) erhalten bleibt
        txt = re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()
        return f"\n\n{'#' * level} {txt}\n\n"

    if name == "p":
        txt = children.strip()
        return f"\n\n{txt}\n\n" if txt else ""

    if name == "strong" or name == "b":
        txt = children.strip()
        return f"**{txt}**" if txt else ""

    if name == "em" or name == "i":
        txt = children.strip()
        return f"*{txt}*" if txt else ""

    if name == "code":
        txt = children.strip()
        return f"`{txt}`" if txt else ""

    if name == "a":
        href = el.get("href", "")
        txt = children.strip() or _inner_text(el).strip()
        if href:
            if href.startswith("/"):
                href = BASE + href
            return f"[{txt}]({href})"
        return txt

    if name == "ul":
        items = [child for child in el.children if getattr(child, "name", None) == "li"]
        body = "".join(_node_to_markdown(li, depth + 1) for li in items)
        return f"\n\n{body}\n\n"

    if name == "ol":
        items = [child for child in el.children if getattr(child, "name", None) == "li"]
        lines = []
        for idx, li in enumerate(items, start=1):
            content = _node_to_markdown(li, depth + 1).strip()
            # Erste Zeile wird nummeriert; verschachtelte Blöcke einrücken
            content = re.sub(r"\s+", " ", content).strip()
            lines.append(f"{idx}. {content}")
        return "\n\n" + "\n".join(lines) + "\n\n"

    if name == "li":
        content = "".join(_node_to_markdown(c, depth + 1) for c in el.children)
        # Verschachtelte Listen extrahieren
        nested = ""
        for c in el.children:
            if getattr(c, "name", None) in ("ul", "ol"):
                nested += _node_to_markdown(c, depth + 1)
        content = re.sub(r"\s+", " ", content).strip()
        indent = "    " * depth
        return f"{indent}- {content}\n" + nested

    if name == "table":
        return _table_to_markdown(el)

    if name in ("blockquote", "pre"):
        txt = children.strip()
        return f"\n\n> {txt}\n\n" if txt else ""

    # div und alles andere: Kinder durchreichen
    return children


def _table_to_markdown(table) -> str:
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        row = []
        for cell in cells:
            txt = re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip()
            row.append(txt)
        rows.append(row)
    if not rows:
        return ""
    # Trennzeile nach der Kopfzeile
    header = "| " + " | ".join(rows[0]) + " |"
    sep = "|" + "|".join(" --- " for _ in rows[0]) + "|"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
    return f"\n\n{header}\n{sep}\n{body}\n\n" if body else f"\n\n{header}\n{sep}\n\n"


def section_content_to_markdown(content_el) -> str:
    md = _node_to_markdown(content_el)
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


_HEADING_LINE_RE = re.compile(r"^(#{3,6})\s+(.*)$")


def split_untersektionen(md: str) -> list[dict] | None:
    """Markdown-Block an internen h3+-Überschriften in Untersektionen zerlegen.

    Liefert ``None``, wenn der Block keine internen Überschriften hat (dann
    bleibt er ein flacher ``inhalt_markdown``). Die Ausgabe ist direkt für
    Check-Entwicklung nutzbar (z. B. „Wie wird geprüft" → 1. Anwendbarkeit,
    2. Prüfung, 3. Hinweise).
    """
    lines = md.split("\n")
    subsections: list[dict] = []
    current_title = ""
    buf: list[str] = []
    seen_heading = False

    for line in lines:
        hm = _HEADING_LINE_RE.match(line)
        if hm:
            if seen_heading:
                subsections.append({
                    "titel": current_title,
                    "inhalt_markdown": "\n".join(buf).strip(),
                })
            seen_heading = True
            current_title = hm.group(2).strip()
            buf = []
        else:
            buf.append(line)

    if not seen_heading:
        return None

    if current_title or any(b.strip() for b in buf):
        subsections.append({
            "titel": current_title,
            "inhalt_markdown": "\n".join(buf).strip(),
        })
    return subsections


# ------------------------------------------------------------------ Parsing

def parse_title(soup: BeautifulSoup) -> tuple[str, str]:
    """Nummer + Titel aus dem <title>-Tag: 'Prüfschritt 9.1.1.1b <Titel> | …'."""
    title_tag = soup.find("title")
    raw = title_tag.get_text(strip=True) if title_tag else ""
    first = raw.split(" | ")[0].strip()
    m = re.match(r"^Prüfschritt\s+(\S+)\s*(.*)$", first, re.S)
    if not m:
        return "", raw
    return m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()


def iter_sections(soup: BeautifulSoup):
    """Liefert (abschnitt_id, titel, content_el) je Collapsible-Block."""
    for el in soup.select("div.Collapsible"):
        heading = el.find(class_="Collapsible__summary-heading")
        content = el.find(class_="Collapsible__content")
        if content is None:
            continue
        # id steht in einem Kind-div (z. B. id="_was_wird_geprueft")
        section_id = ""
        if heading:
            label = heading.find(id=re.compile(r"^_"))
            if label:
                section_id = label.get("id", "").lstrip("_")
            else:
                section_id = re.sub(r"[^a-z0-9_]+", "_", heading.get_text(" ", strip=True).lower()).strip("_")
        title = heading.get_text(" ", strip=True) if heading else ""
        yield section_id, title, content


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_wcag22(soup: BeautifulSoup) -> dict | None:
    """Die 'Einordnung des Prüfschritts nach WCAG 2.2' strukturiert auslesen.

    Die Quelle rendert diesen Block als verschachtelte <section>-Elemente mit
    <h4>Guideline / <h4>Success criterion(s) / <h4>Techniques (mit <h5>-Kategorien
    wie General/HTML/ARIA Techniques und Failures) — keine Tabelle. Die
    Überschrift lautet meist „… nach WCAG 2.2", vereinzelt auch „… nach WCAG 2.1"
    (z. B. 9.3.1.2); die Version wird im Ausgabe-Diktat mitgeführt.
    """
    h3 = None
    wcag_version = ""
    candidates = []
    for cand in soup.find_all("h3"):
        m = re.search(r"Einordnung des Prüfschritts nach WCAG 2\.(\d)",
                      cand.get_text(" ", strip=True))
        if m:
            candidates.append((m.group(1), cand))
    if not candidates:
        return None
    # WCAG 2.2 bevorzugen, sonst die erste gefundene Version
    candidates.sort(key=lambda p: p[0] != "2")
    wcag_version, h3 = candidates[0]
    root = h3.find_parent("section") or h3.find_parent("div") or h3.parent
    if root is None:
        return None

    def section_text(sect) -> str:
        return _clean(sect.get_text(" ", strip=True))

    out: dict = {}
    for h4 in root.find_all("h4"):
        label = _clean(h4.get_text(" ", strip=True)).lower()
        sect = h4.find_parent("section")
        if sect is None:
            continue

        if label == "guideline":
            first_li = sect.find("li")
            if first_li is not None:
                out["guideline"] = _clean(first_li.get_text(" ", strip=True))
        elif label in ("success criterion", "success criteria"):
            first_li = sect.find("li")
            if first_li is not None:
                text = _clean(first_li.get_text(" ", strip=True))
                lm = re.search(r"\(Level\s+(\w+)\)", text)
                out["level"] = lm.group(1) if lm else ""
                out["success_criterion"] = re.sub(r"\s*\(Level\s+\w+\)\s*$", "", text).strip()
        elif label == "techniques":
            # Kategorien (h5) mit ihren Techniken; ohne Kategorien flach sammeln
            categories = {}
            flat: list[str] = []
            for h5 in sect.find_all("h5"):
                cat_sect = h5.find_parent("section")
                items = [_clean(li.get_text(" ", strip=True))
                         for li in cat_sect.find_all("li")] if cat_sect else []
                categories[_clean(h5.get_text(" ", strip=True))] = items
                flat.extend(items)
            if categories:
                out["techniken"] = categories
            elif flat:
                out["techniken"] = flat

    if not out:
        return None
    out["wcag_version"] = f"2.{wcag_version}"
    return out


def extract_test(slug: str, html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    nummer, titel = parse_title(soup)

    abschnitte = []
    for section_id, sect_title, content_el in iter_sections(soup):
        md = section_content_to_markdown(content_el)
        if not md:
            continue
        entry = {"titel": sect_title}
        if section_id:
            entry["id"] = section_id
        unterseiten = split_untersektionen(md)
        if unterseiten:
            entry["untersektionen"] = unterseiten
        else:
            entry["inhalt_markdown"] = md
        abschnitte.append(entry)

    return {
        "quelle": BASE + DETAIL_PREFIX + slug.split("/")[-1],
        "abgerufen": date.today().isoformat(),
        "bitv_nummer": nummer,
        "titel": titel,
        "wcag22": parse_wcag22(soup),
        "abschnitte": abschnitte,
    }


# -------------------------------------------------------------------- Script

def main() -> int:
    parser = argparse.ArgumentParser(description="bitvtest.de-Prüfschritte als JSON extrahieren")
    parser.add_argument("--slug", action="append", default=None,
                        help="Nur diese Slugs extrahieren (testbar); sonst alle.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Zielverzeichnis für die JSON-Dateien")
    parser.add_argument("--delay", type=float, default=DELAY_S, help="Sekunden zwischen Requests")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = "a11y-scanner/bitvtest-extractor (Forschung)"

    slugs = fetch_slugs(session)
    if args.slug:
        wanted = {("/" + s).replace("//", "/") if not s.startswith("/") else s for s in args.slug}
        slugs = [s for s in slugs if s in wanted]
        if not slugs:
            print("Keiner der angegebenen Slugs gefunden.", file=sys.stderr)
            return 2

    index_entries = []
    for idx, slug in enumerate(slugs, start=1):
        url = BASE + slug
        nummer = slug.split("-")[2] if slug.count("-") >= 2 else slug
        print(f"[{idx}/{len(slugs)}] {slug.split('/')[-1][:60]}")
        try:
            html = fetch(url, session)
            test = extract_test(slug, html)
        except Exception as exc:  # noqa: BLE001 — ein Fehler bricht nicht alles ab
            print(f"  ! FEHLER: {exc}")
            index_entries.append({"slug": slug, "status": "fehler", "fehler": str(exc)})
            time.sleep(args.delay)
            continue

        filename = f"{test['bitv_nummer'] or nummer}.json"
        (out_dir / filename).write_text(
            json.dumps(test, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        index_entries.append({
            "slug": slug,
            "status": "ok",
            "datei": filename,
            "bitv_nummer": test["bitv_nummer"],
            "titel": test["titel"],
            "wcag22": test["wcag22"],
        })
        time.sleep(args.delay)

    (out_dir / "_index.json").write_text(
        json.dumps({
            "quelle": BASE + INDEX_PATH,
            "abgerufen": date.today().isoformat(),
            "anzahl": len(index_entries),
            "tests": index_entries,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ok = sum(1 for e in index_entries if e["status"] == "ok")
    print(f"\nFertig: {ok}/{len(slugs)} Prüfschritte nach {out_dir} geschrieben.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
