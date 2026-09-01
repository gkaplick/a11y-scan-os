"""Generiert die 98 BITV-2.0-Prüfschritte als Registry-Einträge + Stub-Checks.

Erzeugt deterministisch aus ``docs/bitvtest/*.json``:

  1. ``app/engine/bitv_steps.py``       — ``BITV_STEPS: list[dict]`` (98 Einträge, Kategorie BITV)
  2. ``app/engine/checks/bitv_*.py``    — je ein Stub-Check (wirft CheckNotImplemented)

Die Registry bindet die Einträge über ``registry.py`` ein (``REGISTRY += BITV_STEPS``);
dieses Skript fasst den Bestand nicht an. Aufruf-Muster:
ohne ``--write`` nur Vorschau, mit ``--write`` werden die Dateien geschrieben.

Aufruf: python scripts/generate_bitv_steps.py [--write]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WRITE = "--write" in sys.argv

# Pfade relativ zu diesem Skript: <repo>/backend/scripts -> Repo-Root
REPO = Path(__file__).resolve().parents[2]
BITVTEST_DIR = REPO / "docs" / "bitvtest"
ENGINE_DIR = REPO / "backend" / "app" / "engine"
CHECKS_DIR = ENGINE_DIR / "checks"
OUT_MODULE = ENGINE_DIR / "bitv_steps.py"

INDEX_ANZAHL = 98

UMLAUTE = [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")]

STUB_TEMPLATE = '''"""{test_id} — {title} (Stub). Noch kein Algorithmus."""
from __future__ import annotations

from ._base import CheckContext, CheckNotImplemented


async def {check}(ctx: CheckContext):
    """{test_id} — {title} (Stub)."""
    raise CheckNotImplemented("{test_id}: noch kein Algorithmus")
'''


def slugify(text: str) -> str:
    """Titel -> UPPER_SNAKE (Umlaute transliterieren, Nicht-Alnum -> '_')."""
    s = text.lower()
    for src, dst in UMLAUTE:
        s = s.replace(src, dst)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_").upper()


def check_name(test_id: str) -> str:
    """bitv_9_1_4_3_kontraste_von_texten_ausreichend -> check_kontraste_von_texten_ausreichend.

    System-Präfix und
    Nummern-Segmente (inkl. Suffix wie '1a') werden abgeworfen.
    """
    parts = test_id.lower().split("_")[1:]
    while parts and re.fullmatch(r"\d+[a-z]?", parts[0]):
        parts.pop(0)
    if not parts:
        return "check_" + test_id.lower().replace("-", "_")
    return "check_" + "_".join(parts)


def clean(text) -> str:
    """Markdown-Text: Whitespace-Ketten auf ein Leerzeichen reduzieren."""
    return re.sub(r"\s+", " ", text or "").strip()


def num_key(nummer: str) -> tuple:
    """Natürliche Sortierung: '9.1.4.3' < '9.1.4.10'; '9.1.1.1a' am Listenende."""
    parts: list = []
    for seg in nummer.split("."):
        m = re.match(r"(\d+)(.*)", seg)
        parts.append(int(m.group(1)))
        parts.append(m.group(2))
    return tuple(parts)


def section_by_id(abschnitte: list, abs_id: str) -> dict | None:
    for s in abschnitte:
        if s.get("id") == abs_id:
            return s
    return None


def build_entry(d: dict) -> dict:
    nummer = d["bitv_nummer"]
    titel = d["titel"]
    wcag = d.get("wcag22") or {}
    wcag_level = wcag.get("level") or ""
    level = "KANN" if wcag_level == "AAA" else "MUSS"
    test_id = f"BITV_{nummer.replace('.', '_')}_{slugify(titel)}"

    abschnitte = d.get("abschnitte") or []
    was = section_by_id(abschnitte, "was_wird_geprüft")
    description = clean(was.get("inhalt_markdown")) if was else ""
    test_hint = ""
    wie = section_by_id(abschnitte, "wie_wird_geprüft")
    if wie:
        for sub in wie.get("untersektionen") or []:
            if sub.get("titel", "").startswith("1."):
                test_hint = clean(sub.get("inhalt_markdown"))
                break

    return {
        "id": nummer,
        "test_id": test_id,
        "title": titel,
        "suite": "bitv",
        "level": level,
        "wcag_level": wcag_level,
        "category": "BITV",
        "responsibility": "technisch",
        "priority": "mittel",
        "type": "syntax",
        "desktop_only": False,
        "module": test_id.lower(),
        "check": check_name(test_id),
        "status": "stub",
        "description": description,
        "solution": "",
        "test_hint": test_hint,
    }


def format_entry(e: dict) -> str:
    lines = ["    {"]
    for key, value in e.items():
        lines.append(f"        {key!r}: {value!r},")
    lines.append("    },")
    return "\n".join(lines)


def module_content(entries: list[dict]) -> str:
    body = "\n".join(format_entry(e) for e in entries)
    return f'''"""BITV-2.0-Prüfschritte — maschinell generiert.

Erzeugt von scripts/generate_bitv_steps.py — nicht von Hand bearbeiten.
Quelle: docs/bitvtest/*.json (strukturierte Referenz, angelehnt an die Vorgaben der BITV 2.0).
Die 98 Prüfschritte sind Kategorie-BITV-Einträge; die Registry hängt sie an:
``registry.py`` -> ``REGISTRY += BITV_STEPS``.
"""
from __future__ import annotations

BITV_STEPS: list[dict] = [
{body}
]
'''


def main() -> int:
    files = sorted(p for p in BITVTEST_DIR.glob("*.json") if p.name != "_index.json")
    steps = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    steps.sort(key=lambda d: num_key(d["bitv_nummer"]))

    print(f"Prüfschritt-JSONs gefunden: {len(steps)} (erwartet: {INDEX_ANZAHL})")
    if len(steps) != INDEX_ANZAHL:
        print(f"FEHLER: {BITVTEST_DIR} enthält {len(steps)} statt {INDEX_ANZAHL} Dateien")
        return 1

    entries = [build_entry(d) for d in steps]

    # Integritäts-Checks vor dem Schreiben
    ids = [e["test_id"] for e in entries]
    assert len(ids) == len(set(ids)), "doppelte test_id"
    for e in entries:
        assert e["module"] == e["test_id"].lower()
        assert e["status"] == "stub" and e["check"]
        ident = e["check"]
        assert ident.isidentifier(), f"kein gültiger Funktionsname: {ident}"
    kategorie_level = {e["level"] for e in entries}
    assert kategorie_level <= {"MUSS", "KANN"}, kategorie_level
    assert {e["category"] for e in entries} == {"BITV"}
    assert {e["suite"] for e in entries} == {"bitv"}

    stub_paths = [CHECKS_DIR / f"{e['module']}.py" for e in entries]
    if WRITE:
        OUT_MODULE.write_text(module_content(entries), encoding="utf-8")
        created = 0
        for e, fpath in zip(entries, stub_paths):
            if fpath.exists():
                continue
            fpath.write_text(
                STUB_TEMPLATE.format(test_id=e["test_id"], title=e["title"],
                                     check=e["check"]),
                encoding="utf-8",
            )
            created += 1
        print(f"bitv_steps.py geschrieben: {OUT_MODULE.name} ({len(entries)} Einträge)")
        print(f"Stub-Dateien geschrieben: {created} (von {len(stub_paths)})")
    else:
        print("Vorschau (ohne --write, keine Dateien angelegt):")
        print(f"  bitv_steps.py -> {OUT_MODULE.name} ({len(entries)} Einträge)")
        print(f"  Stub-Dateien  -> {len(stub_paths)} x checks/bitv_*.py")
        sample = next(e for e in entries if e["test_id"].startswith("BITV_9_1_4_3_"))
        print("\nBeispiel-Eintrag:")
        print(format_entry(sample))
        print("\nBeispiel-Datei bitv_9_1_4_3_kontraste_von_texten_ausreichend.py:")
        print(STUB_TEMPLATE.format(test_id=sample["test_id"], title=sample["title"],
                                   check=sample["check"]).rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
