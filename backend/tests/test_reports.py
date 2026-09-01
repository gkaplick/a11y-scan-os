"""
Smoke-Tests des TXT-Report-Generators.

Der TXT-Report muss aus einem echten ``ResultsOut`` fehlerfrei erzeugen.
Die Fixture-Seite stammt aus test_results._insert_fixture.
"""
from __future__ import annotations

from app.engine.results import build_results
from app.models import Finding, Job, Page, TestRecord
from app.reports import generate_txt_report
from tests.test_results import _en_kap9_fixture, _insert_fixture


async def _build_results(db_session):
    job_id = _insert_fixture(db_session)
    return await build_results(job_id)


async def test_txt_report_structure(db_session):
    results = await _build_results(db_session)
    report = generate_txt_report(results)
    assert isinstance(report, str)

    for marker in (
        "SYSTEM-BEWERTUNG",
        "ZUSAMMENFASSUNG",
        "FEHLER NACH TEST",
        "BESTANDENE KRITERIEN",
        "EN 301 549 — ERGEBNIS JE KRITERIUM",
        "MANUELL ZU PRÜFEN",
        "MULTI-RESOLUTION",
        "FEHLER NACH URL",
        "Tote Links (404)",
        "Nicht-Text-Inhalte",
        "https://example.com/kontakt",
    ):
        assert marker in report, f"TXT-Report enthält '{marker}' nicht"


async def test_txt_report_aufloesungsunabhaengig_statt_nonepx(db_session):
    """resolution=None (auflösungsunabhängig) wird sauber gelabelt, nie „Nonepx".

    Der frühere Bug: ``_multi_resolution`` nahm ``{None}`` in die
    Auflösungs-Liste auf → „FEHLER (bei Nonepx)“. Ein Resolution-Check mit
    DOM-Befund (ohne resolution) UND Überlauf-Befund (bei 320px) zeigt beide
    Teile — der Überlauf trägt die echte Breite, der DOM-Befund ist
    auflösungsunabhängig.
    """
    job_id = "job-nonepx"
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done"))
    db_session.add(TestRecord(
        job_id=job_id, test_id="BITV_9_1_4_10_INHALTE_BRECHEN_UM",
        title="Inhalte brechen um", suite="bitv", level="SOLLTE", wcag_level="AA",
        category="BITV", number="9.1.4.10", responsibility="technisch",
        priority="hoch", type="resolution", status="implemented",
    ))
    db_session.add_all([
        Finding(job_id=job_id, test_id="BITV_9_1_4_10_INHALTE_BRECHEN_UM",
                url="https://example.com/", dom_path="head",
                message="Kein viewport-Meta-Tag gefunden — responsive Umbrüche gefährdet",
                resolution=None, level="SOLLTE", wcag_level="AA",
                responsibility="technisch", priority="hoch"),
        Finding(job_id=job_id, test_id="BITV_9_1_4_10_INHALTE_BRECHEN_UM",
                url="https://example.com/", dom_path="html",
                message="Horizontaler Überlauf: Dokument 400px breiter als Viewport 320px",
                resolution=320, level="SOLLTE", wcag_level="AA",
                responsibility="technisch", priority="hoch"),
    ])
    db_session.add(Page(job_id=job_id, url="https://example.com/", http_status=200, ok=True))
    db_session.commit()

    results = await build_results(job_id)
    assert results is not None
    report = generate_txt_report(results)

    assert "Nonepx" not in report
    assert "auflösungsunabhängig" in report
    # MULTI-RESOLUTION: beide Auflösungs-Anteile benannt (kein „Nonepx").
    assert ("BITV_9_1_4_10_INHALTE_BRECHEN_UM: FEHLER "
            "(bei 320px; auflösungsunabhängig) — Inhalte brechen um") in report
    # Einzel-Befund: DOM-Befund ohne Suffix, Überlauf mit echter Breite.
    assert "- Kein viewport-Meta-Tag gefunden — responsive Umbrüche gefährdet\n" in report
    assert "Horizontaler Überlauf: Dokument 400px breiter als Viewport 320px (bei 320px)" in report


def _build_en_results(db_session):
    """EN-Fixture: A-/AA-Befund + EN-5.2 + AAA (erweitert) → EN-Sektion gefüllt."""
    job_id = "job-en-report"
    _en_kap9_fixture(db_session, job_id, findings={
        "WCAG_1_1_1_IMG_ALT": True,        # verbindlich, schlägt das EN-Urteil
        "WCAG_1_4_3_CONTRAST_AA": False,   # verbindlich, bestanden
        "WCAG_1_4_6_CONTRAST_AAA": False,  # erweitert, bestanden
    }, mit_en_kapitel=True)
    return job_id


async def test_txt_report_enthaelt_en_sektion(db_session):
    """TXT-Report: EN-Abschnitt nach Kapitel, verbindlich/erweitert markiert."""
    job_id = _build_en_results(db_session)
    results = await build_results(job_id)
    report = generate_txt_report(results)

    assert "EN 301 549 — ERGEBNIS JE KRITERIUM" in report
    assert "Gesamturteil: nicht bestanden" in report
    assert "1 erweitert (AAA, informatorisch)" in report
    # Kapitel-Gliederung: EN 5.2 → Kapitel 5, WCAG-Tests → Kapitel 9
    assert "Kapitel 5 — Allgemeine Anforderungen" in report
    assert "Kapitel 9 — Web (WCAG 2.1)" in report
    assert "[BESTANDEN] 5.2 Aktivierung von Barrierefreiheitsfunktionen (verbindlich)" in report
    assert "[NICHT BESTANDEN] 1.1.1 Nicht-Text-Inhalte (verbindlich)" in report
    assert "[BESTANDEN] 1.4.6 Kontrast (Erhöht) (erweitert)" in report


async def test_txt_report_schliesst_nicht_relevant_aus(db_session):
    """Deaktivierte Kriterien (nicht_relevant) erscheinen nicht im EN-Bericht.

    Der Nutzer blendet Kriterien über die Übersicht aus (Status
    nicht_relevant) — sie wurden vom Scan ausgeschlossen und gehören nicht in
    die EN-Sektion des TXT-Reports. In results.tests bleiben sie erhalten
    (Ergebnis „nicht anwendbar"), damit die Übersicht konsistent ist. Die
    EN-Sektion ist alles bis zur Manuell-Liste; „bestandene Kriterien" stehen
    davor, die deaktivierten erscheinen dort nicht (Ergebnis nicht_anwendbar).
    """
    job_id = _build_en_results(db_session)
    # WCAG 1.4.3 (EN-Kapitel 9) + EN 5.2 vom Nutzer deaktiviert.
    from app.models import TestRecord

    for tid in ("WCAG_1_4_3_CONTRAST_AA", "EN_5_2_ACTIVATION"):
        rec = db_session.query(TestRecord).filter_by(job_id=job_id, test_id=tid).one()
        rec.status = "nicht_relevant"
    db_session.commit()

    results = await build_results(job_id)
    assert results is not None

    # results.tests behält die deaktivierten Kriterien (Ergebnis „nicht anwendbar").
    by_id = {t.test_id: t for t in results.tests}
    assert by_id["WCAG_1_4_3_CONTRAST_AA"].result == "nicht_anwendbar"
    assert by_id["EN_5_2_ACTIVATION"].result == "nicht_anwendbar"

    report = generate_txt_report(results)
    assert "EN 301 549 — ERGEBNIS JE KRITERIUM" in report
    en_part = report.split("MANUELL ZU PRÜFEN")[0]
    # Deaktivierte erscheinen NICHT in der EN-Sektion …
    assert "1.4.3 Kontrast (Minimum)" not in en_part
    # EN-5.2 nur über ihre EN-Sektions-Zeile geprüft: der gleichnamige BITV-Test
    # „Aktivierung von Barrierefreiheitsfunktionen" (aktiv) steht zu Recht in
    # den BESTANDENEN KRITERIEN und trägt dort keinen [BESTANDEN]-Vorspann.
    assert "[BESTANDEN] 5.2 Aktivierung von Barrierefreiheitsfunktionen" not in en_part
    # … aktive Kriterien aber weiterhin.
    assert "[NICHT BESTANDEN] 1.1.1 Nicht-Text-Inhalte (verbindlich)" in en_part
    assert "[BESTANDEN] 1.4.6 Kontrast (Erhöht) (erweitert)" in en_part
