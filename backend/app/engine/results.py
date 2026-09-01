"""
Aggregation der Scan-Ergebnisse zu den zwei Frontend-Perspektiven:

- ``by_test``: je Fehlerart/Test die gefundenen URLs
- ``by_url``:  je URL die gefundenen Fehler

Beide werden aus den persistierten ``Finding``-Zeilen des Jobs abgeleitet —
die Metadaten (Level, Verantwortung, …) kommen aus den ``TestRecord``-Snapshots
des Laufs (Fallback auf das aktuelle Registry).
"""
from __future__ import annotations

import asyncio
import os
from collections import OrderedDict

from ..db import SessionLocal
from ..models import Finding, Job, Page, TestRecord
from ..schemas import (
    FindingOut,
    LevelZaehlung,
    ResultByTest,
    ResultByUrl,
    ResultsOut,
    SystemBewertungOut,
    TestOut,
)
from . import registry as reg
from .screenshots import job_screenshot_dir

# Pseudo-Tests ohne Registry-Eintrag (vom Runner angelegt) → lesbarer Titel
_PSEUDO_TITLES = {"LINKS_404": "Tote Links (404)"}

# Reihenfolge der Testsysteme in der Bewertung (BITV zuerst, wie im UI)
_SYSTEM_ORDER = ["BITV", "WCAG", "EN 301 549"]
_WCAG_LEVELS = ["A", "AA", "AAA"]

# Outcome → Anzeige-Ergebnis pro Test (an TestOut.result).
_ERGEBNIS = {
    "passed": "bestanden",
    "failed": "nicht_bestanden",
    "excluded": "nicht_anwendbar",
    "not_auto": "nicht_bewertet",
}


def _en_kind(t: TestOut) -> str | None:
    """Einordnung eines Kriteriums in der EN 301 549.

    EN 301 549 verweist für Web (Kapitel 9) vollständig auf WCAG 2.1: Die
    Erfolgskriterien der Stufen A und AA sind verbindlich einzuhalten, die
    Stufe AAA wird informatorisch als „erweiterte Kriterien" aufgeführt
    (EU-Durchführungsbeschluss 2021/1339 / EN 301 549 V3.2.1). Die EN-eigenen
    Kapitel (5–12) sind grundsätzlich verbindlich; Kriterien, die dort auf
    WCAG-AAA verweisen (z. B. EN 11.7), gelten ebenfalls als erweitert.
    BITV-Kriterien sind kein EN-Kriterium → None.
    """
    if t.category not in ("WCAG", "EN 301 549"):
        return None
    return "erweitert" if t.wcag_level == "AAA" else "verbindlich"


def _build_en_bewertung(
    ts: list[TestOut],
    outcomes: dict[str, str],
) -> SystemBewertungOut | None:
    """Gesamturteil für EN 301 549 (EN-Tests + WCAG-Tests als Kapitel 9).

    Nur die verbindlichen Kriterien (WCAG A/AA sowie EN-Kapitel 5–12)
    bestimmen das Urteil. Erweiterte Kriterien (WCAG AAA) sind informatorisch
    und werden nur separat gezählt (`erweitert`) — sie können das Urteil nie
    kippen. None, wenn kein einziges Kriterium bewertbar oder nicht
    automatisiert ist (z. B. alle deaktiviert).
    """
    verbindlich = [t for t in ts if t.en_kind == "verbindlich"]
    erweitert = [t for t in ts if t.en_kind == "erweitert"]
    bewertbar = [t for t in verbindlich if outcomes[t.test_id] in ("passed", "failed")]
    failed = [t for t in verbindlich if outcomes[t.test_id] == "failed"]
    nicht_auto = sum(1 for t in verbindlich if outcomes[t.test_id] == "not_auto")
    erweitert_bewertet = [t for t in erweitert if outcomes[t.test_id] in ("passed", "failed")]
    if not bewertbar and nicht_auto == 0 and not erweitert_bewertet:
        return None
    urteil = "nicht bestanden" if failed else ("bestanden" if bewertbar else "nicht bewertbar")
    return SystemBewertungOut(
        system="EN 301 549",
        urteil=urteil,
        gesamt=len(bewertbar),
        bestanden=len(bewertbar) - len(failed),
        nicht_bestanden=len(failed),
        nicht_automatisiert=nicht_auto,
        erweitert=len(erweitert_bewertet),
    )


def _build_system_bewertung(
    tests: list[TestOut],
    findings: list[Finding],
    assessments: dict[str, str] | None = None,
):
    """Gesamturteil je Testsystem (BITV / WCAG / EN 301 549), pro Projekt.

    Urteilslogik (User-Vorgabe):
    - BITV/EN sind binär: Default je Kriterium ist „nicht anwendbar" (= zählt
      als bestanden); jeder Befund überschreibt zu „nicht bestanden" und ist
      projektweit bindend (ein Befund irgendwo reicht).
    - WCAG ist abgestuft: je Kriterium bestanden/nicht bestanden, Gesamturteil
      mit erzieltem Konformitätsniveau (A/AA/AAA).
    - Nur Status ``implemented`` wird bewertet; Stub/manual zählen als
      „nicht automatisiert" (ein nicht implementierter Check ist kein Bestehen).
    - Manuell bewertete Tests (assessments: test_id → "erfuellt" |
      "nicht_erfuellt" | "nicht_anwendbar") zählen als bewertbar: erfuellt und
      nicht_anwendbar = bestanden, nicht_erfuellt = nicht bestanden.
    - EN 301 549: Das EN-System umfasst die EN-Kriterien (Kapitel 5–12) PLUS
      die WCAG-Kriterien als EN-Kapitel 9 (EN verweist für Web vollständig auf
      WCAG 2.1). Verbindlich sind WCAG A/AA und die EN-Kapitel 5–12; WCAG-AAA
      („erweiterte Kriterien") sind informatorisch und werden nur separat in
      ``erweitert`` gezählt — sie kippen das EN-Urteil nie. EN-Kriterien erben
      ihr Ergebnis von den Quell-Tests (``en_sources``): schlägt eine Quelle
      fehl, gilt der EN-Test als nicht bestanden; sind alle Quellen deaktiviert
      („nicht_relevant"), erbt er „nicht relevant".
    """
    finding_test_ids = {f.test_id for f in findings}
    assessments = assessments or {}
    assessed = {
        tid: val for tid, val in assessments.items()
        if val in ("erfuellt", "nicht_erfuellt", "nicht_anwendbar")
    }
    by_system: dict[str, list[TestOut]] = {}
    ts_by_id: dict[str, TestOut] = {}
    for t in tests:
        if not t.category:      # Pseudo-Tests (z. B. LINKS_404) ausschließen
            continue
        by_system.setdefault(t.category, []).append(t)
        ts_by_id[t.test_id] = t

    def _source_outcome(s: TestOut) -> str:
        """Outcome eines BITV/WCAG-Quelltests (ohne EN-Vererbung).

        Manuell bewertete Kriterien (aus ``manual_assessments``) zählen über
        ihre Dropdown-Bewertung — der Runner führt sie als Status "manual".
        Implementiert schlägt die Bewertung (echte Befunde).
        """
        if s.status == "nicht_relevant":
            return "excluded"
        if s.status == "implemented":
            return "failed" if s.test_id in finding_test_ids else "passed"
        if s.test_id in assessed:
            return "failed" if assessed[s.test_id] == "nicht_erfuellt" else "passed"
        return "not_auto"

    def _outcome(t: TestOut) -> str:
        """Effektives Ergebnis eines Tests: passed|failed|not_auto|excluded."""
        if t.category == "EN 301 549":
            if t.status == "nicht_relevant":
                return "excluded"
            srcs = [ts_by_id[sid] for sid in t.en_sources if sid in ts_by_id]
            if not srcs:
                return "not_auto"
            relevant = [s for s in srcs if s.status != "nicht_relevant"]
            if not relevant:
                # Alle Quellen deaktiviert → EN-Test erbt „nicht relevant".
                return "excluded"
            src_out = [_source_outcome(s) for s in relevant]
            if any(o == "failed" for o in src_out):
                return "failed"
            if any(o in ("passed", "failed") for o in src_out):
                return "passed"
            return "not_auto"
        return _source_outcome(t)

    # EN-Kind (verbindlich/erweitert) vorab an jedem Kriterium setzen.
    for t in tests:
        t.en_kind = _en_kind(t)

    bewertungen: list[SystemBewertungOut] = []
    for system in _SYSTEM_ORDER:
        ts = list(by_system.get(system, []))
        if system == "EN 301 549":
            # EN-Kapitel 9 = die WCAG-Kriterien: EN 301 549 verweist für Web
            # vollständig auf WCAG 2.1 (A/AA verbindlich, AAA erweitert). Die
            # WCAG-Tests fließen also in BEIDE Systeme ein — in das eigene
            # „WCAG"-Urteil und als Kapitel-9-Anteil des EN-Systems.
            ts += list(by_system.get("WCAG", []))
        if not ts:
            continue
        outcomes = {t.test_id: _outcome(t) for t in ts}
        # Ergebnis je Kriterium ans TestOut hängen (für die Detailansicht).
        for t in ts:
            t.result = _ERGEBNIS[outcomes[t.test_id]]

        if system == "EN 301 549":
            en = _build_en_bewertung(ts, outcomes)
            if en is not None:
                bewertungen.append(en)
            continue

        # Bewertbar = effektiv bestanden oder nicht bestanden (implementiert
        # oder manuell bewertet). Nicht automatisiert = Stub/manual ohne
        # manuelle Bewertung. Vom Nutzer deaktivierte Tests (Status
        # "nicht_relevant") zählen nirgendwo — weder als bestanden noch als
        # Fehler noch als "nicht automatisiert".
        bewertbar = [t for t in ts if outcomes[t.test_id] in ("passed", "failed")]
        failed = [t for t in ts if outcomes[t.test_id] == "failed"]
        nicht_auto = sum(1 for t in ts if outcomes[t.test_id] == "not_auto")
        # Wurden ALLE Tests eines Systems deaktiviert (keine bewertbaren und
        # keine automatisierten), gibt es kein Urteil — das System
        # verschwindet aus der Bewertung.
        if not bewertbar and nicht_auto == 0:
            continue

        urteil = "nicht bestanden" if failed else ("bestanden" if bewertbar else "nicht bewertbar")
        if system != "WCAG":
            # BITV/EN sind binär: keine Level-Aufschlüsselung. (BITV ist
            # binär (MUSS), die Karte zeigt Erfüllt/Nicht erfüllt + Fortschritt.)
            bewertungen.append(SystemBewertungOut(
                system=system,
                urteil=urteil,
                gesamt=len(bewertbar),
                bestanden=len(bewertbar) - len(failed),
                nicht_bestanden=len(failed),
                nicht_automatisiert=nicht_auto,
            ))
            continue

        # --- WCAG: Level-Verteilung + erzieltes Konformitätsniveau ---
        verteilung = []
        for level in _WCAG_LEVELS:
            lv = [t for t in bewertbar if t.wcag_level == level]
            lv_failed = [t for t in lv if outcomes[t.test_id] == "failed"]
            verteilung.append(LevelZaehlung(
                level=level,
                gesamt=len(lv),
                bestanden=len(lv) - len(lv_failed),
                nicht_bestanden=len(lv_failed),
            ))

        # Konformitätsstufen-Semantik: schlägt ein A-Kriterium fehl → kein
        # Level; schlägt (nur) AA fehl → Level A; (nur) AAA fehl → Level AA;
        # sonst höchstes vorhandenes Level.
        if failed and any(t.wcag_level == "A" for t in failed):
            niveau = "kein Level erfüllt"
        elif failed and any(t.wcag_level == "AA" for t in failed):
            niveau = "A"
        elif failed and any(t.wcag_level == "AAA" for t in failed):
            niveau = "AA"
        else:
            niveau = next(
                (lv for lv in ("AAA", "AA", "A")
                 if any(t.wcag_level == lv for t in bewertbar)),
                None,
            )

        bewertungen.append(SystemBewertungOut(
            system=system,
            urteil=urteil,
            gesamt=len(bewertbar),
            bestanden=len(bewertbar) - len(failed),
            nicht_bestanden=len(failed),
            nicht_automatisiert=nicht_auto,
            niveau=niveau,
            level_verteilung=verteilung,
        ))
    return bewertungen


def _vorhandene_screenshot_ids(job_id: str) -> set[int]:
    """Befund-IDs, zu denen im Job-Ordner eine Screenshot-Datei existiert.

    Das Frontend zeigt nur dann ein Thumbnail an (und fragt das PNG nur dann
    ab), wenn ``screenshot`` True ist — so entstehen keine 404-Requests für
    Befunde, deren Element beim Scan nicht aufgelöst werden konnte.
    """
    verzeichnis = job_screenshot_dir(job_id)
    try:
        eintraege = os.listdir(verzeichnis)
    except OSError:
        return set()
    ids = set()
    for name in eintraege:
        basis, endung = os.path.splitext(name)
        if endung.lower() == ".png" and basis.isdigit():
            ids.add(int(basis))
    return ids


def _finding_out(f: Finding, shot_ids: set[int] | None = None) -> FindingOut:
    return FindingOut(
        id=f.id,
        screenshot=(f.id in shot_ids) if shot_ids is not None else False,
        test_id=f.test_id,
        url=f.url,
        dom_path=f.dom_path,
        message=f.message,
        detail=f.detail,
        resolution=f.resolution,
        number=f.number,
        category=f.category,
        level=f.level,
        wcag_level=f.wcag_level,
        responsibility=f.responsibility,
        priority=f.priority,
    )


def _test_out(record: TestRecord, assessments: dict[str, str] | None = None) -> TestOut:
    reg_entry = reg.get_test(record.test_id)
    return TestOut(
        id=reg_entry.get("id", record.test_id) if reg_entry else record.test_id,
        test_id=record.test_id,
        title=record.title,
        suite=record.suite,
        level=record.level,
        wcag_level=record.wcag_level,
        category=record.category,
        responsibility=record.responsibility,
        priority=record.priority,
        type=record.type,
        status=record.status,
        description=reg_entry.get("description", "") if reg_entry else "",
        solution=reg_entry.get("solution", "") if reg_entry else "",
        test_hint=reg_entry.get("test_hint", "") if reg_entry else "",
        assessment=(assessments or {}).get(record.test_id),
        en_sources=reg.get_en_source_test_ids(record.test_id),
    )


def _load_job_data(job_id: str):
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None:
            return None
        pages = session.query(Page).filter(Page.job_id == job_id).order_by(Page.id).all()
        findings = (
            session.query(Finding).filter(Finding.job_id == job_id).order_by(Finding.id).all()
        )
        records = (
            session.query(TestRecord).filter(TestRecord.job_id == job_id).order_by(TestRecord.id).all()
        )
        return job, pages, findings, records


async def build_results(job_id: str) -> ResultsOut | None:
    """Aggregiert die beiden Perspektiven für einen Job (None wenn Job fehlt)."""
    data = await asyncio.to_thread(_load_job_data, job_id)
    if data is None:
        return None
    job, pages, findings, records = data

    assessments = (job.options or {}).get("manual_assessments") or {}
    shot_ids = _vorhandene_screenshot_ids(job_id)
    tests = [_test_out(r, assessments) for r in records]
    # „Manuell zu prüfen" = Status manual ODER mit manueller Dropdown-Bewertung
    # (BITV 6/7/11/12-Kriterien). Diese erscheinen damit in der Manuell-Liste
    # statt als automatisiert (User-Vorgabe: es gibt keine Stubs mehr).
    manual_tests = [
        t for t in tests
        if t.status != "nicht_relevant"
        and (t.status == "manual" or t.assessment is not None)
    ]
    system_bewertung = _build_system_bewertung(tests, findings, assessments)

    # --- Perspektive 1: by_test ---
    by_test_map: "OrderedDict[str, dict]" = OrderedDict()
    for f in findings:
        if f.test_id not in by_test_map:
            record = next((r for r in records if r.test_id == f.test_id), None)
            by_test_map[f.test_id] = {
                "title": record.title if record else _PSEUDO_TITLES.get(f.test_id, f.test_id),
                "suite": record.suite if record else "",
                "level": record.level if record else "",
                "wcag_level": record.wcag_level if record else None,
                "number": record.number if record else None,
                "category": record.category if record else "",
                "responsibility": record.responsibility if record else "",
                "priority": record.priority if record else "",
                "findings": [],
                "urls_seen": [],
            }
        entry = by_test_map[f.test_id]
        entry["findings"].append(_finding_out(f, shot_ids))
        if f.url not in entry["urls_seen"]:
            entry["urls_seen"].append(f.url)

    by_test = [
        ResultByTest(
            test_id=tid,
            title=entry["title"],
            suite=entry["suite"],
            level=entry["level"],
            wcag_level=entry["wcag_level"],
            number=entry["number"],
            category=entry["category"],
            responsibility=entry["responsibility"],
            priority=entry["priority"],
            count=len(entry["findings"]),
            urls=entry["urls_seen"],
            findings=entry["findings"],
        )
        for tid, entry in by_test_map.items()
    ]

    # --- Perspektive 2: by_url ---
    by_url_map: "OrderedDict[str, dict]" = OrderedDict()
    for page in pages:
        by_url_map[page.url] = {
            "http_status": page.http_status,
            "ok": page.ok,
            "error": page.error,
            "findings": [],
        }
    for f in findings:
        if f.url in by_url_map:
            by_url_map[f.url]["findings"].append(_finding_out(f, shot_ids))

    by_url = [
        ResultByUrl(
            url=url,
            http_status=entry["http_status"],
            ok=entry["ok"],
            error=entry["error"],
            finding_count=len(entry["findings"]),
            findings=entry["findings"],
        )
        for url, entry in by_url_map.items()
    ]

    return ResultsOut(
        job_id=job.id,
        suite=job.suite,
        status=job.status,
        by_test=by_test,
        by_url=by_url,
        page_count=len(pages),
        total_findings=len(findings),
        tests=tests,
        manual_tests=manual_tests,
        system_bewertung=system_bewertung,
    )
