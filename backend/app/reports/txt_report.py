"""
TXT-Report — gliedert den Bericht nach dem strukturierten ``ResultsOut``-Modell
und spiegelt die Ergebnis-Seite des Web-Frontends (/jobs/<id>):

1. Titel + Kopf (Projekt, Suite-Label, Status, Seiten, Befunde)
2. SYSTEM-BEWERTUNG (BITV / WCAG / EN 301 549 — je System Urteil + Zähler;
   WCAG mit Konformitätsniveau und Level-Aufschlüsselung A/AA/AAA)
3. ZUSAMMENFASSUNG (Datum/Zeit, Seiten, Level-Statistik, MUSS/SOLLTE/KANN
   „Sich aus dem Audit ergebende Aufgaben" + Prioritäten)
4. FEHLER NACH TEST (gruppiert nach BITV-Kategorie wie die Frontend-Ansicht
   „Nach Test"; je Test Titel, Metadaten, URLs und Befunde — Beschreibung/
   Lösung/Prüfhinweis je Test genau einmal statt je Befund)
5. BESTANDENE KRITERIEN (Kriterien ohne Befunde, „bestanden")
6. EN 301 549 — ERGEBNIS JE KRITERIUM (nach Kapitel, verbindlich/erweitert)
7. MANUELL ZU PRÜFEN (Checkliste mit Bewertungs-Status)
8. MULTI-RESOLUTION-TESTS (Auflösungen der Befunde)
9. 404-URLS & Seiten mit 404-Links
10. FEHLER NACH URL (je URL mit DOM-Pfad + Standard, sortiert MUSS→KANN)

Auflösungs-Semantik: ``resolution=None`` heißt auflösungsunabhängig — der
Befund gilt bei jeder Renderbreite (z. B. Syntax-/DOM-Befunde). Wo ein
Resolution-Check die echte Breite kennt (z. B. Überlauf bei 320px), wird sie
als „bei Xpx" ausgegeben.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from ..schemas import JobOut, ResultsOut, TestOut

_SEP = "=" * 72
_THIN = "-" * 72

# Suite-Labels wie im Frontend (SUITE_LABELS in pages/jobs/[id].vue).
_SUITE_LABELS = {
    "bitv": "BITV 2.0",
    "wcag": "WCAG 2.1",
    "all": "BITV 2.0 + WCAG 2.1",
}

# BITV-Kategorien in Frontend-Reihenfolge (ResultByTest.vue: MUSS→SOLLTE→KANN,
# Rest = „Ohne normatives Level").
_LEVEL_ORDER = ("MUSS", "SOLLTE", "KANN")
_LEVEL_GROUP_LABELS = {
    "MUSS": "Muss erfüllt sein",
    "SOLLTE": "Sollte erfüllt sein",
    "KANN": "Kann erfüllt sein",
    "Weitere": "Ohne normatives Level",
}

_URTEIL_TEXT = {
    "bestanden": "Bestanden",
    "nicht bestanden": "Nicht bestanden",
    "nicht bewertbar": "Nicht bewertbar",
}

# Manuelle Bewertungen (system_bewertung/assessments → ASSESSMENT_META im
# Frontend): Schlüssel sind die Backend-Werte, Labels wie im Web.
_ASSESSMENT_TEXT = {
    "erfuellt": "Erfüllt",
    "nicht_erfuellt": "Nicht erfüllt",
    "nicht_anwendbar": "Nicht anwendbar",
}

_WCAG_LEVEL_NAME = {"A": "Minimum", "AA": "Standard", "AAA": "Erweitert"}

# EN 301 549: Kapitel-Gliederung des EN-Systems (Kapitel 9 = Web = WCAG 2.1).
_EN_CHAPTER_LABELS = {
    "5": "Allgemeine Anforderungen",
    "6": "Zwei-Wege-Sprachkommunikation",
    "7": "Kommunikationstechnik mit Videofunktionen",
    "9": "Web (WCAG 2.1)",
    "11": "Software",
    "12": "Dokumentation und Unterstützungsdienste",
}
_EN_RESULT_TEXT = {
    "bestanden": "BESTANDEN",
    "nicht_bestanden": "NICHT BESTANDEN",
    "nicht_anwendbar": "nicht anwendbar",
    "nicht_bewertet": "nicht bewertet",
}


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%d.%m.%Y um %H:%M:%S (UTC)")


def _res_label(resolution: int | None) -> str:
    """Auflösungs-Suffix eines einzelnen Befunds: ``None`` = auflösungsunabhängig."""
    if resolution is None:
        return "auflösungsunabhängig"
    return f"bei {resolution}px"


def _res_summary(resolutions: set) -> str:
    """Distincte Auflösungen einer Befund-Gruppe, z. B. ``bei 320px, 1920px``.

    ``resolution=None`` (auflösungsunabhängig) wird separat benannt; mischt
    ein Test beides (z. B. DOM-Befund + Überlauf bei 320px), stehen beide Teile.
    """
    widths = sorted({r for r in resolutions if r is not None})
    parts: list[str] = []
    if widths:
        parts.append("bei " + ", ".join(f"{w}px" for w in widths))
    if any(r is None for r in resolutions):
        parts.append("auflösungsunabhängig")
    return "; ".join(parts) if parts else "auflösungsunabhängig"


def _finding_prefix(f) -> str:
    """Level-Badge + WCAG-Level-Badge wie im Frontend (``[MUSS] [A]``)."""
    parts = []
    if f.level:
        parts.append(f"[{f.level}]")
    if f.wcag_level:
        parts.append(f"[{f.wcag_level}]")
    return " ".join(parts)


def _criteria_label(f) -> str:
    parts = []
    if f.category:
        parts.append(f"{f.category} {f.number}" if f.number else f.category)
    if f.wcag_level:
        parts.append(f"Level {f.wcag_level}")
    return " | ".join(parts)


def _test_out(results: ResultsOut, test_id: str) -> TestOut | None:
    """Registry-Snapshot des Laufs zu einer test_id (None für Pseudo-Tests)."""
    return next((t for t in results.tests if t.test_id == test_id), None)


def _summary(results: ResultsOut) -> list[str]:
    lines: list[str] = []

    by_url = results.by_url
    pages_ok = sum(1 for u in by_url if u.ok and u.finding_count == 0)
    pages_errors = sum(1 for u in by_url if u.ok and u.finding_count > 0)
    pages_404 = sum(1 for u in by_url if u.http_status == 404)

    # Seiten je WCAG-Level mit mind. einem Fehler
    for level in ("A", "AA", "AAA"):
        urls = {f.url for u in by_url for f in u.findings if f.wcag_level == level}
        lines.append(f"Seiten mit Level-{level}-Fehlern: {len(urls)}")

    # Tests: nur ausgeführte (implemented) zählen
    executed = [t for t in results.tests if t.status == "implemented"]
    failed_ids = {t.test_id for t in results.by_test}
    failed = [t for t in executed if t.test_id in failed_ids]
    passed = [t for t in executed if t.test_id not in failed_ids]

    lines.append(f"Seiten bestanden: {pages_ok}")
    lines.append(f"Seiten nicht bestanden: {pages_errors}")
    lines.append(f"404-Seiten: {pages_404}")
    disabled_tests = [t for t in results.tests if t.status == "nicht_relevant"]
    if disabled_tests:
        lines.append(f"Als 'nicht relevant' deaktivierte Tests: {len(disabled_tests)}")
    lines.append("")
    lines.append("Tests (nur automatisierte Kriterien):")
    for level in ("A", "AA", "AAA"):
        lvl_failed = [t for t in failed if t.wcag_level == level]
        lvl_passed = [t for t in passed if t.wcag_level == level]
        if lvl_failed or lvl_passed:
            lines.append(f"  Level {level}: {len(lvl_passed)} bestanden / {len(lvl_failed)} fehlgeschlagen")

    lines.append("")
    lines.append("Sich aus dem Audit ergebende Aufgaben:")
    for cat in ("MUSS", "SOLLTE", "KANN"):
        cat_failed = [t for t in failed if t.level == cat]
        tech = sum(1 for t in cat_failed if t.responsibility == "technisch")
        red = sum(1 for t in cat_failed if t.responsibility == "redaktionell")
        lines.append(f"  {cat}-Anforderungen:")
        lines.append(f"    → Technisch: {tech}")
        lines.append(f"    → Redaktionell: {red}")
        lines.append(f"    → Gesamt: {len(cat_failed)}")

    lines.append("  Prioritäten:")
    for prio in ("hoch", "mittel", "niedrig"):
        lines.append(f"    → {prio.capitalize()}: {sum(1 for t in failed if t.priority == prio)}")

    return lines


def _system_bewertung(results: ResultsOut) -> list[str]:
    """Je System ein Urteil wie die SystemSummary-Karten im Frontend."""
    lines: list[str] = []
    if not results.system_bewertung:
        return ["  Keine System-Bewertung verfügbar."]
    for s in results.system_bewertung:
        urteil = _URTEIL_TEXT.get(s.urteil, s.urteil)
        head = f"  {s.system} — {urteil}"
        if s.system == "WCAG" and s.niveau:
            niveau = "kein Level erfüllt" if s.niveau == "kein Level erfüllt" else f"Level {s.niveau}"
            head += f"  (Konformitätsniveau: {niveau})"
        lines.append(head)

        if s.system == "WCAG" and s.level_verteilung:
            for lv in s.level_verteilung:
                name = _WCAG_LEVEL_NAME.get(lv.level, "")
                lines.append(
                    f"    {lv.level} {name}: {lv.bestanden} Erfüllt / "
                    f"{lv.nicht_bestanden} Verletzt (Gesamt {lv.gesamt})"
                )
            tb = sum(lv.bestanden for lv in s.level_verteilung)
            tn = sum(lv.nicht_bestanden for lv in s.level_verteilung)
            lines.append(f"    Summe: {tb} Erfüllt / {tn} Verletzt")
        else:
            bewertet = (s.bestanden or 0) + (s.nicht_bestanden or 0)
            quote = round(s.bestanden / bewertet * 100) if bewertet else 0
            lines.append(f"    Erfüllt: {s.bestanden} · Nicht erfüllt: {s.nicht_bestanden} (Quote: {quote}%)")

        if s.nicht_automatisiert:
            lines.append(f"    {s.nicht_automatisiert} nicht automatisiert (manuell zu prüfen)")
        if s.system == "EN 301 549":
            hint = "Nur verbindliche Kriterien (WCAG A/AA + EN-Kapitel 5–12) bestimmen das Urteil."
            if s.erweitert:
                hint += f" {s.erweitert} erweitert (AAA) informatorisch."
            lines.append(f"    {hint}")
    return lines


def _by_test_section(results: ResultsOut) -> list[str]:
    """FEHLER NACH TEST — gruppiert nach BITV-Kategorie (wie ResultByTest.vue)."""
    lines: list[str] = []
    if not results.by_test:
        return ["  Keine Fehler gefunden."]
    groups: dict[str, list] = {lv: [] for lv in _LEVEL_ORDER}
    groups["Weitere"] = []
    for bt in results.by_test:
        (groups.get(bt.level, groups["Weitere"])).append(bt)
    for level in (*_LEVEL_ORDER, "Weitere"):
        tests = groups[level]
        if not tests:
            continue
        label = _LEVEL_GROUP_LABELS[level]
        fehler = sum(t.count for t in tests)
        lines.append(f"{label} ({len(tests)} Kriterien · {fehler} Fehler)")
        lines.append(_THIN)
        for bt in tests:
            reg_t = _test_out(results, bt.test_id)
            lines.append("")
            wcag = f" · Level {bt.wcag_level}" if bt.wcag_level else ""
            std = f" · {bt.number}" if bt.number else ""
            lines.append(f"  {bt.title}{wcag}{std}")
            lines.append(
                f"    {bt.count}× auf {len(bt.urls)} Seite(n) · "
                f"Auflösung(en): {_res_summary({f.resolution for f in bt.findings})}"
            )
            if bt.urls:
                lines.append(f"    Betroffene Seiten: {', '.join(bt.urls)}")
            for f in bt.findings:
                res = f" (bei {f.resolution}px)" if f.resolution else ""
                lines.append(f"    - {f.message}{res}")
                if f.url:
                    lines.append(f"        URL: {f.url}")
                if f.dom_path:
                    lines.append(f"        Pfad: {f.dom_path}")
                if f.detail:
                    lines.append(f"        Detail: {f.detail}")
                crit = _criteria_label(f)
                if crit:
                    lines.append(f"        Standard: {crit}")
            if reg_t:
                if reg_t.description:
                    lines.append(f"    Beschreibung: {reg_t.description}")
                if reg_t.solution:
                    lines.append(f"    Lösung: {reg_t.solution}")
                if reg_t.test_hint:
                    lines.append(f"    Prüfhinweis: {reg_t.test_hint}")
        lines.append("")
    return lines


def _bestandene_kriterien(results: ResultsOut) -> list[str]:
    """Grüne „Bestandene Kriterien"-Sektion des Frontends (result == bestanden)."""
    passed = [t for t in results.tests if t.result == "bestanden" and t.status != "nicht_relevant"]
    if not passed:
        return ["  Keine bestandenen Kriterien in dieser Suite."]
    lines: list[str] = []
    for t in sorted(passed, key=lambda x: (x.id or x.test_id)):
        wcag = f"[{t.wcag_level}] " if t.wcag_level else ""
        lines.append(f"  {wcag}{t.id or t.test_id} {t.title}")
    return lines


def _en_chapter(t) -> str | None:
    """Kapitel eines EN-System-Kriteriums (für die EN-Report-Gliederung).

    EN-Tests tragen die EN-Kapitel-Nummer im ``test_id``-Präfix (``EN_6_…`` →
    6); WCAG-Tests zählen im EN-System als EN-Kapitel 9 (EN 301 549 verweist
    für Web vollständig auf WCAG 2.1). BITV-Tests gehören nicht ins EN-System.
    """
    if t.category == "EN 301 549":
        m = re.match(r"EN_(\d+)", t.test_id or "")
        return m.group(1) if m else None
    if t.category == "WCAG":
        return "9"
    return None


def _en_section(results: ResultsOut) -> list[str]:
    """EN 301 549: Ergebnis je Kriterium, nach Kapitel gegliedert.

    Verbindlich = WCAG A/AA und EN-Kapitel 5–12; erweitert (AAA) ist
    informatorisch und kippt das Urteil nicht. Die Ergebnis-Werte kommen aus
    ``results.tests`` (``result``/``en_kind``), das Gesamturteil aus
    ``system_bewertung``.
    """
    # Vom Nutzer deaktivierte Kriterien (nicht_relevant) gehören nicht in den
    # Bericht — sie wurden vom Scan ausgeschlossen.
    en_tests = [t for t in results.tests if _en_chapter(t) and t.status != "nicht_relevant"]
    if not en_tests:
        return ["Keine EN-301-549-Kriterien in dieser Suite."]
    lines: list[str] = []
    en_bew = next((s for s in results.system_bewertung if s.system == "EN 301 549"), None)
    if en_bew:
        lines.append(
            f"Gesamturteil: {en_bew.urteil} — {en_bew.bestanden} bestanden / "
            f"{en_bew.nicht_bestanden} nicht bestanden / "
            f"{en_bew.nicht_automatisiert} nicht automatisiert"
            + (f" / {en_bew.erweitert} erweitert (AAA, informatorisch)" if en_bew.erweitert else "")
        )
        lines.append(
            "Hinweis: Verbindlich = WCAG A/AA und EN-Kapitel 5–12. "
            "Erweiterte Kriterien (AAA) sind informatorisch."
        )
    chapters = sorted({_en_chapter(t) for t in en_tests if _en_chapter(t)}, key=int)
    for ch in chapters:
        label = _EN_CHAPTER_LABELS.get(ch, f"Kapitel {ch}")
        lines.append("")
        lines.append(f"Kapitel {ch} — {label}")
        lines.append(_THIN)
        chapter_tests = sorted(
            (t for t in en_tests if _en_chapter(t) == ch),
            key=lambda t: (t.id or t.test_id),
        )
        for t in chapter_tests:
            result = _EN_RESULT_TEXT.get(t.result or "nicht_bewertet", t.result or "nicht_bewertet")
            kind = f" ({t.en_kind})" if t.en_kind else ""
            lines.append(f"  [{result}] {t.id or t.test_id} {t.title}{kind}")
    return lines


def _manuell(results: ResultsOut) -> list[str]:
    """MANUELL ZU PRÜFEN — Checkliste (Status manual oder mit Bewertung)."""
    if not results.manual_tests:
        return ["  Keine manuellen Kriterien in dieser Suite."]
    lines: list[str] = []
    for t in sorted(results.manual_tests, key=lambda x: (x.id or x.test_id)):
        meta = " · ".join(
            x for x in (
                t.id or t.test_id,
                f"[{t.wcag_level}]" if t.wcag_level else "",
                t.category,
                f"Verantwortlichkeit: {t.responsibility}",
                f"Priorität: {t.priority}",
            ) if x
        )
        bew = _ASSESSMENT_TEXT.get(t.assessment, t.assessment) if t.assessment else None
        head = f"  {t.title}  ({meta})"
        if bew:
            head += f"  → Bewertung: {bew}"
        lines.append(head)
        if t.description:
            lines.append(f"    Was wird getestet: {t.description}")
        if t.solution:
            lines.append(f"    Lösung: {t.solution}")
        if t.test_hint:
            lines.append(f"    Prüfhinweis: {t.test_hint}")
    return lines


def _multi_resolution(results: ResultsOut) -> list[str]:
    res_tests = [t for t in results.tests if t.type == "resolution"]
    if not res_tests:
        return ["Keine auflösungsabhängigen Tests in dieser Suite."]
    lines: list[str] = []
    failed_ids = {t.test_id for t in results.by_test}
    for t in sorted(res_tests, key=lambda x: x.test_id):
        my_res = {f.resolution for ft in results.by_test if ft.test_id == t.test_id for f in ft.findings}
        status = "FEHLER" if t.test_id in failed_ids else "ok"
        suffix = f" ({_res_summary(my_res)})" if my_res else ""
        lines.append(f"  {t.test_id}: {status}{suffix} — {t.title}")
    return lines


def _fehler_nach_url(results: ResultsOut) -> list[str]:
    """FEHLER NACH URL — je Seite, Befunde sortiert nach BITV-Kategorie."""
    lines: list[str] = []
    any_errors = False
    for u in results.by_url:
        if not u.findings:
            continue
        any_errors = True
        lines.append("")
        status = f" (HTTP {u.http_status})" if u.http_status else ""
        lines.append(f"Seite: {u.url}{status}  —  {len(u.findings)} Fehler")
        lines.append(_THIN)
        ranked = sorted(
            u.findings,
            key=lambda f: (_LEVEL_ORDER.index(f.level) if f.level in _LEVEL_ORDER else 99, f.dom_path),
        )
        for f in ranked:
            res = f" (bei {f.resolution}px)" if f.resolution else ""
            lines.append(f"  {_finding_prefix(f)} {f.message}{res}")
            if f.dom_path:
                lines.append(f"    Pfad: {f.dom_path}")
            crit = _criteria_label(f)
            if crit:
                lines.append(f"    Standard: {crit}")
            if f.detail:
                lines.append(f"    Detail: {f.detail}")
    if not any_errors:
        lines.append("  Keine Fehler gefunden.")
    return lines


def generate_txt_report(results: ResultsOut, job: JobOut | None = None) -> str:
    url = job.url if job else results.job_id
    suite = job.suite if job else results.suite
    suite_label = _SUITE_LABELS.get(suite, suite)

    out: list[str] = [
        _SEP,
        "Barrierefreiheitsprüfung - Automatisierter Report",
        _SEP,
        f"Projekt: {url}",
        f"Suite: {suite_label}",
        f"Status: {results.status}",
        f"Geprüfte Seiten: {results.page_count}",
        f"Befunde gesamt: {results.total_findings}",
        f"Report generiert am {_now_str()} mit automatisiertem Barrierefreiheits-Scanner",
        "",
        "SYSTEM-BEWERTUNG",
        _THIN,
        * _system_bewertung(results),
        "",
        "ZUSAMMENFASSUNG",
        _THIN,
        f"Datum/Zeit: {_now_str()}",
        f"Geprüfte Seiten: {results.page_count}",
        * _summary(results),
        "",
        "FEHLER NACH TEST",
        _THIN,
        * _by_test_section(results),
        "BESTANDENE KRITERIEN",
        _THIN,
        * _bestandene_kriterien(results),
        "",
        "EN 301 549 — ERGEBNIS JE KRITERIUM",
        _THIN,
        * _en_section(results),
        "",
        "MANUELL ZU PRÜFEN",
        _THIN,
        * _manuell(results),
        "",
        "MULTI-RESOLUTION-TESTS",
        _THIN,
        * _multi_resolution(results),
        "",
        "404-URLS UND SEITEN MIT 404-LINKS",
        _THIN,
    ]

    # 404-Seiten (gecrawlte URLs, die 404 lieferten)
    pages_404 = [u for u in results.by_url if u.http_status == 404]
    if pages_404:
        out.append("404-Seiten (gecrawlte URLs):")
        for u in pages_404:
            out.append(f"  {u.url}")
    else:
        out.append("Keine 404-Seiten gefunden.")

    # Tote Links aus dem LINKS_404-Findings (url = Fundseite, dom_path = Ziel)
    broken = [f for ft in results.by_test if ft.test_id == "LINKS_404" for f in ft.findings]
    if broken:
        out.append("")
        out.append("Seiten mit 404-Links:")
        by_page: dict[str, list[str]] = {}
        for f in broken:
            by_page.setdefault(f.url, []).append(f.dom_path)
        for page, links in sorted(by_page.items()):
            out.append(f"  Seite: {page}")
            for link in sorted(set(links)):
                out.append(f"    → {link}")
    else:
        out.append("")
        out.append("Keine toten Links gefunden.")

    out += [
        "",
        "FEHLER NACH URL",
        _THIN,
        * _fehler_nach_url(results),
        "",
        _SEP,
        f"Report generiert am {_now_str()} mit automatisiertem Barrierefreiheits-Scanner",
        _SEP,
    ]
    return "\n".join(out) + "\n"
