"""
Tests der Ergebnis-Aggregation (engine/results.py) gegen feste Fixtures.

Zentral sind die beiden Frontend-Perspektiven:
- by_test:  je Fehlerart → betroffene URLs (mit Titel aus Registry bzw. _PSEUDO_TITLES)
- by_url:   je URL → gefundene Fehler
"""
from __future__ import annotations

from app.engine.results import build_results
from app.models import Finding, Job, Page, TestRecord


def _insert_fixture(db_session) -> str:
    """Legt einen Job mit 2 Seiten, 3 Findings und 3 TestRecords an. Gibt job_id zurück."""
    job_id = "job-1"
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done"))

    # Registry-Snapshots des Laufs (number = einzige Norm-Nummer, keine Querweise)
    db_session.add_all([
        TestRecord(job_id=job_id, test_id="WCAG_1_1_1_IMG_ALT", title="Nicht-Text-Inhalte (Textalternative)",
                   suite="bitv", level="MUSS", wcag_level="A", category="WCAG",
                   number="1.1.1", responsibility="redaktionell",
                   priority="hoch", type="syntax", status="implemented"),
        TestRecord(job_id=job_id, test_id="WCAG_1_3_2_MEANINGFUL_SEQUENCE", title="Bedeutung durch Reihenfolge",
                   suite="bitv", level="MUSS", wcag_level="A", category="WCAG",
                   number="1.3.2", responsibility="technisch",
                   priority="mittel", type="manual", status="manual"),
        TestRecord(job_id=job_id, test_id="WCAG_2_1_1_KEYBOARD", title="Tastatur",
                   suite="bitv", level="MUSS", wcag_level="A", category="WCAG",
                   number="2.1.1", responsibility="technisch",
                   priority="hoch", type="resolution", status="implemented"),
    ])

    # Seiten
    db_session.add_all([
        Page(job_id=job_id, url="https://example.com/", http_status=200, ok=True),
        Page(job_id=job_id, url="https://example.com/kontakt", http_status=200, ok=True),
    ])

    # Findings
    db_session.add_all([
        Finding(job_id=job_id, test_id="WCAG_1_1_1_IMG_ALT", url="https://example.com/",
                dom_path="body > img#logo", message="Bild ohne alt-Attribut",
                level="MUSS", wcag_level="A", responsibility="redaktionell", priority="hoch"),
        Finding(job_id=job_id, test_id="WCAG_1_1_1_IMG_ALT", url="https://example.com/kontakt",
                dom_path="body > main > img", message="Bild ohne alt-Attribut",
                level="MUSS", wcag_level="A", responsibility="redaktionell", priority="hoch"),
        # Pseudo-Test (kein Registry-Eintrag) — Titel-Fallback muss greifen
        Finding(job_id=job_id, test_id="LINKS_404", url="https://example.com/",
                dom_path="https://example.com/toter-link", message="Toter Link (404)",
                detail="Linkziel: https://example.com/toter-link",
                level="MUSS", wcag_level="", responsibility="technisch", priority="mittel"),
    ])
    db_session.commit()
    return job_id


async def test_by_test_grouping(db_session):
    job_id = _insert_fixture(db_session)
    results = await build_results(job_id)
    assert results is not None

    by_test = results.by_test
    ids = [t.test_id for t in by_test]
    assert "WCAG_1_1_1_IMG_ALT" in ids
    assert "LINKS_404" in ids

    img_alt = next(t for t in by_test if t.test_id == "WCAG_1_1_1_IMG_ALT")
    assert img_alt.count == 2
    assert set(img_alt.urls) == {"https://example.com/", "https://example.com/kontakt"}
    assert img_alt.title == "Nicht-Text-Inhalte (Textalternative)"
    assert img_alt.level == "MUSS"

    links404 = next(t for t in by_test if t.test_id == "LINKS_404")
    assert links404.title == "Tote Links (404)"          # _PSEUDO_TITLES-Fallback
    assert links404.count == 1
    assert links404.urls == ["https://example.com/"]


async def test_by_url_grouping(db_session):
    job_id = _insert_fixture(db_session)
    results = await build_results(job_id)
    by_url = results.by_url

    assert len(by_url) == 2
    start = next(u for u in by_url if u.url == "https://example.com/")
    assert start.finding_count == 2
    assert start.ok is True
    assert {f.test_id for f in start.findings} == {"WCAG_1_1_1_IMG_ALT", "LINKS_404"}

    kontakt = next(u for u in by_url if u.url == "https://example.com/kontakt")
    assert kontakt.finding_count == 1
    assert kontakt.findings[0].test_id == "WCAG_1_1_1_IMG_ALT"


async def test_totals_and_test_lists(db_session):
    job_id = _insert_fixture(db_session)
    results = await build_results(job_id)

    assert results.page_count == 2
    assert results.total_findings == 3
    assert results.job_id == job_id
    assert results.status == "done"

    assert {t.test_id for t in results.manual_tests} == {"WCAG_1_3_2_MEANINGFUL_SEQUENCE"}
    assert {t.test_id for t in results.tests} >= {"WCAG_1_1_1_IMG_ALT"}


async def test_missing_job_returns_none(db_session):
    assert await build_results("nicht-vorhanden") is None


# ------------------------------------------- "Nicht relevante" Tests (Toggle)

async def test_disabled_tests_excluded_from_assessment(db_session):
    """Status 'nicht_relevant' (vom Nutzer deaktiviert) zählt in keinem Urteil."""
    job_id = "job-disabled"
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done"))
    db_session.add_all([
        TestRecord(job_id=job_id, test_id="WCAG_1_1_1_IMG_ALT", title="Nicht-Text-Inhalte",
                   suite="bitv", level="MUSS", wcag_level="A", category="WCAG",
                   number="1.1.1", responsibility="redaktionell",
                   priority="hoch", type="syntax", status="implemented"),
        TestRecord(job_id=job_id, test_id="WCAG_2_1_1_KEYBOARD", title="Tastatur",
                   suite="bitv", level="MUSS", wcag_level="A", category="WCAG",
                   number="2.1.1", responsibility="technisch",
                   priority="hoch", type="resolution", status="nicht_relevant"),
    ])
    db_session.add(Page(job_id=job_id, url="https://example.com/", http_status=200, ok=True))
    db_session.commit()

    results = await build_results(job_id)
    assert results is not None
    wcag = next(s for s in results.system_bewertung if s.system == "WCAG")
    assert wcag.gesamt == 1                       # nur implemented zählt
    assert wcag.bestanden == 1
    assert wcag.nicht_automatisiert == 0          # nicht_relevant ≠ Stub/manual
    # Der deaktivierte Test bleibt im Snapshot sichtbar (aber unberücksichtigt)
    assert any(t.test_id == "WCAG_2_1_1_KEYBOARD" and t.status == "nicht_relevant"
               for t in results.tests)


async def test_system_with_only_disabled_tests_hidden(db_session):
    """Sind ALLE Tests eines Systems deaktiviert, verschwindet das System ganz."""
    job_id = "job-all-disabled"
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done"))
    db_session.add(TestRecord(
        job_id=job_id, test_id="BITV_9_1_2_1_ALTERNATIVEN_FUER_AUDIODATEIEN_UND_STUMME_VIDEOS",
        title="Audio-Transkript", suite="bitv", level="MUSS", wcag_level="A",
        category="BITV", number="9.1.2.1", responsibility="redaktionell",
        priority="mittel", type="syntax", status="nicht_relevant",
    ))
    db_session.commit()

    results = await build_results(job_id)
    assert results is not None
    assert not any(s.system == "BITV" for s in results.system_bewertung)


# ------------------------------------------- Manuelle Bewertungen (Dropdowns)

async def test_manual_assessment_nicht_erfuellt_schlaegt_system(db_session):
    """Manuell bewerteter BITV-Test ('nicht_erfuellt') → System 'nicht bestanden'."""
    job_id = "job-manual-nicht-erfuellt"
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done",
                       options={"manual_assessments": {
                           "BITV_6_1_AUDIOBANDBREITE_FUER_SPRACHE": "nicht_erfuellt"}}))
    db_session.add(TestRecord(
        job_id=job_id, test_id="BITV_6_1_AUDIOBANDBREITE_FUER_SPRACHE",
        title="Audiobandbreite für Sprache", suite="bitv", level="MUSS", wcag_level=None,
        category="BITV", number="6.1", responsibility="redaktionell",
        priority="mittel", type="syntax", status="manual",
    ))
    db_session.add(Page(job_id=job_id, url="https://example.com/", http_status=200, ok=True))
    db_session.commit()

    results = await build_results(job_id)
    assert results is not None
    bitv = next(s for s in results.system_bewertung if s.system == "BITV")
    assert bitv.gesamt == 1
    assert bitv.nicht_bestanden == 1
    assert bitv.bestanden == 0
    assert bitv.urteil == "nicht bestanden"
    # Das assessment hängt am TestOut und der Test erscheint in der Manual-Liste
    t = next(x for x in results.tests if x.test_id == "BITV_6_1_AUDIOBANDBREITE_FUER_SPRACHE")
    assert t.assessment == "nicht_erfuellt"
    assert t.test_id in {m.test_id for m in results.manual_tests}


async def test_manual_assessment_nicht_anwendbar_zaehlt_als_bestanden(db_session):
    """Default 'nicht_anwendbar' zählt als bestanden (kein Fehler)."""
    job_id = "job-manual-na"
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done",
                       options={"manual_assessments": {
                           "BITV_6_1_AUDIOBANDBREITE_FUER_SPRACHE": "nicht_anwendbar"}}))
    db_session.add(TestRecord(
        job_id=job_id, test_id="BITV_6_1_AUDIOBANDBREITE_FUER_SPRACHE",
        title="Audiobandbreite für Sprache", suite="bitv", level="MUSS", wcag_level=None,
        category="BITV", number="6.1", responsibility="redaktionell",
        priority="mittel", type="syntax", status="manual",
    ))
    db_session.commit()

    results = await build_results(job_id)
    assert results is not None
    bitv = next(s for s in results.system_bewertung if s.system == "BITV")
    assert bitv.gesamt == 1
    assert bitv.nicht_bestanden == 0
    assert bitv.bestanden == 1
    assert bitv.urteil == "bestanden"


async def test_deaktivierter_manueller_test_zaehlt_nicht(db_session):
    """Deaktivierter manueller Test (Status 'nicht_relevant') gewinnt über das
    assessment: obwohl 'nicht_erfuellt' übermittelt wurde, zählt der Test nicht."""
    job_id = "job-manual-deaktiviert"
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done",
                       options={"manual_assessments": {
                           "BITV_6_1_AUDIOBANDBREITE_FUER_SPRACHE": "nicht_erfuellt"}}))
    db_session.add(TestRecord(
        job_id=job_id, test_id="BITV_6_1_AUDIOBANDBREITE_FUER_SPRACHE",
        title="Audiobandbreite für Sprache", suite="bitv", level="MUSS", wcag_level=None,
        category="BITV", number="6.1", responsibility="redaktionell",
        priority="mittel", type="syntax", status="nicht_relevant",
    ))
    db_session.commit()

    results = await build_results(job_id)
    assert results is not None
    # Kein bewertbarer und kein nicht automatisierter Test → BITV verschwindet.
    assert not any(s.system == "BITV" for s in results.system_bewertung)
    assert not any(t.test_id == "BITV_6_1_AUDIOBANDBREITE_FUER_SPRACHE" for t in results.manual_tests)


# ------------------------------------------- EN 301 549: Ergebnis-Vererbung

def _en_fixture(db_session, job_id: str, source_status: str, finding: bool):
    """EN 5.2 (Stub) + BITV 5.2 (Quelltest) als TestRecords anlegen."""
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done"))
    db_session.add_all([
        TestRecord(job_id=job_id, test_id="EN_5_2_ACTIVATION",
                   title="Aktivierung von Barrierefreiheitsfunktionen",
                   suite="bitv", level="MUSS", wcag_level=None, category="EN 301 549",
                   number="5.2", responsibility="technisch", priority="mittel",
                   type="syntax", status="stub"),
        TestRecord(job_id=job_id,
                   test_id="BITV_5_2_AKTIVIERUNG_VON_BARRIEREFREIHEITSFUNKTIONEN",
                   title="Aktivierung von Barrierefreiheitsfunktionen",
                   suite="bitv", level="MUSS", wcag_level=None, category="BITV",
                   number="5.2", responsibility="technisch", priority="mittel",
                   type="syntax", status=source_status),
    ])
    if finding:
        db_session.add(Finding(job_id=job_id,
                               test_id="BITV_5_2_AKTIVIERUNG_VON_BARRIEREFREIHEITSFUNKTIONEN",
                               url="https://example.com/", dom_path="body",
                               message="Barrierefreiheitsfunktion fehlt",
                               level="MUSS", wcag_level=None,
                               responsibility="technisch", priority="mittel"))
    db_session.add(Page(job_id=job_id, url="https://example.com/", http_status=200, ok=True))
    db_session.commit()


async def test_en_erbt_nicht_bestanden_von_bitv_befund(db_session):
    """EN-Test erbt 'nicht bestanden', wenn der BITV-Quelltest einen Befund hat."""
    job_id = "job-en-fail"
    _en_fixture(db_session, job_id, source_status="implemented", finding=True)

    results = await build_results(job_id)
    assert results is not None
    en = next(s for s in results.system_bewertung if s.system == "EN 301 549")
    assert en.gesamt == 1
    assert en.nicht_bestanden == 1
    assert en.bestanden == 0
    # Der EN-Test ist separat ausgewiesen, hat aber keinen eigenen Befund.
    assert not any(t.test_id == "EN_5_2_ACTIVATION" for t in results.by_test)
    en_t = next(t for t in results.tests if t.test_id == "EN_5_2_ACTIVATION")
    assert "BITV_5_2_AKTIVIERUNG_VON_BARRIEREFREIHEITSFUNKTIONEN" in en_t.en_sources


async def test_en_erbt_bestanden_von_bitv_ohne_befund(db_session):
    """EN-Test erbt 'bestanden', wenn der Quelltest ohne Befund durchläuft."""
    job_id = "job-en-pass"
    _en_fixture(db_session, job_id, source_status="implemented", finding=False)

    results = await build_results(job_id)
    assert results is not None
    en = next(s for s in results.system_bewertung if s.system == "EN 301 549")
    assert en.gesamt == 1
    assert en.nicht_bestanden == 0
    assert en.bestanden == 1
    assert en.urteil == "bestanden"


async def test_en_erbt_nicht_relevant_wenn_quelle_deaktiviert(db_session):
    """Alle Quellen deaktiviert → EN-Test ebenfalls 'nicht relevant' (kein Urteil)."""
    job_id = "job-en-disabled"
    _en_fixture(db_session, job_id, source_status="nicht_relevant", finding=False)

    results = await build_results(job_id)
    assert results is not None
    assert not any(s.system == "EN 301 549" for s in results.system_bewertung)


# ------------------- EN 301 549: Kapitel 9 + verbindlich/erweitert ---------

def _en_kap9_fixture(db_session, job_id: str, findings: dict[str, bool],
                     mit_en_kapitel: bool = False):
    """WCAG-A/AA/AAA-Tests (EN-Kapitel 9) + optional EN-5.2 mit BITV-Quelle.

    findings: test_id → True wenn ein Befund existiert.
    """
    db_session.add(Job(id=job_id, url="https://example.com/", suite="all", status="done"))
    db_session.add_all([
        TestRecord(job_id=job_id, test_id="WCAG_1_1_1_IMG_ALT", title="Nicht-Text-Inhalte",
                   suite="bitv", level="MUSS", wcag_level="A", category="WCAG",
                   number="1.1.1", responsibility="redaktionell",
                   priority="hoch", type="syntax", status="implemented"),
        TestRecord(job_id=job_id, test_id="WCAG_1_4_3_CONTRAST_AA", title="Kontrast (Minimum)",
                   suite="bitv", level="SOLLTE", wcag_level="AA", category="WCAG",
                   number="1.4.3", responsibility="technisch",
                   priority="hoch", type="resolution", status="implemented"),
        TestRecord(job_id=job_id, test_id="WCAG_1_4_6_CONTRAST_AAA", title="Kontrast (Erhöht)",
                   suite="wcag", level="KANN", wcag_level="AAA", category="WCAG",
                   number="1.4.6", responsibility="technisch",
                   priority="niedrig", type="resolution", status="implemented"),
    ])
    for tid, has_finding in findings.items():
        if has_finding:
            db_session.add(Finding(job_id=job_id, test_id=tid, url="https://example.com/",
                                   dom_path="body", message="Befund",
                                   level="MUSS", wcag_level="A",
                                   responsibility="technisch", priority="hoch"))
    if mit_en_kapitel:
        db_session.add_all([
            TestRecord(job_id=job_id, test_id="EN_5_2_ACTIVATION",
                       title="Aktivierung von Barrierefreiheitsfunktionen",
                       suite="bitv", level="MUSS", wcag_level=None, category="EN 301 549",
                       number="5.2", responsibility="technisch", priority="mittel",
                       type="syntax", status="stub"),
            TestRecord(job_id=job_id,
                       test_id="BITV_5_2_AKTIVIERUNG_VON_BARRIEREFREIHEITSFUNKTIONEN",
                       title="Aktivierung von Barrierefreiheitsfunktionen",
                       suite="bitv", level="MUSS", wcag_level=None, category="BITV",
                       number="5.2", responsibility="technisch", priority="mittel",
                       type="syntax", status="implemented"),
        ])
    db_session.add(Page(job_id=job_id, url="https://example.com/", http_status=200, ok=True))
    db_session.commit()


async def test_en_verbindlich_zaehlt_wcag_a_aa_als_kapitel_9(db_session):
    """WCAG-A/AA-Befunde (EN-Kapitel 9) schlagen das EN-Urteil; AAA ist erweitert."""
    job_id = "job-en-kap9"
    _en_kap9_fixture(db_session, job_id, findings={
        "WCAG_1_1_1_IMG_ALT": True,       # A → verbindlich, schlägt das EN-Urteil
        "WCAG_1_4_3_CONTRAST_AA": False,  # AA → verbindlich, bestanden
        "WCAG_1_4_6_CONTRAST_AAA": False,  # AAA → erweitert (informatorisch)
    }, mit_en_kapitel=True)

    results = await build_results(job_id)
    assert results is not None
    en = next(s for s in results.system_bewertung if s.system == "EN 301 549")
    assert en.gesamt == 3          # EN 5.2 + WCAG 1.1.1 + WCAG 1.4.3
    assert en.nicht_bestanden == 1  # der A-Befund
    assert en.bestanden == 2
    assert en.urteil == "nicht bestanden"
    assert en.erweitert == 1       # WCAG 1.4.6 (AAA) separat gezählt


async def test_en_erweitert_fail_kippt_urteil_nicht(db_session):
    """Nur ein AAA-Fehler (erweitert) lässt das EN-Urteil unangetastet."""
    job_id = "job-en-erweitert"
    _en_kap9_fixture(db_session, job_id, findings={
        "WCAG_1_1_1_IMG_ALT": False,
        "WCAG_1_4_3_CONTRAST_AA": False,
        "WCAG_1_4_6_CONTRAST_AAA": True,  # AAA-Fehler → informatorisch
    })

    results = await build_results(job_id)
    assert results is not None
    en = next(s for s in results.system_bewertung if s.system == "EN 301 549")
    assert en.urteil == "bestanden"
    assert en.gesamt == 2          # nur verbindliche (A + AA)
    assert en.nicht_bestanden == 0
    assert en.bestanden == 2
    assert en.erweitert == 1       # der AAA-Fehler zählt separat, kippt nicht


async def test_en_kind_und_result_haengen_am_test(db_session):
    """Je Kriterium: result (bestanden/nicht_bestanden/…) + en_kind (verbindlich/erweitert)."""
    job_id = "job-en-kind"
    _en_kap9_fixture(db_session, job_id, findings={
        "WCAG_1_1_1_IMG_ALT": True,
        "WCAG_1_4_3_CONTRAST_AA": False,
        "WCAG_1_4_6_CONTRAST_AAA": False,
    }, mit_en_kapitel=True)

    results = await build_results(job_id)
    by_id = {t.test_id: t for t in results.tests}
    assert by_id["WCAG_1_1_1_IMG_ALT"].result == "nicht_bestanden"
    assert by_id["WCAG_1_1_1_IMG_ALT"].en_kind == "verbindlich"
    assert by_id["WCAG_1_4_3_CONTRAST_AA"].result == "bestanden"
    assert by_id["WCAG_1_4_3_CONTRAST_AA"].en_kind == "verbindlich"
    assert by_id["WCAG_1_4_6_CONTRAST_AAA"].en_kind == "erweitert"
    assert by_id["WCAG_1_4_6_CONTRAST_AAA"].result == "bestanden"
    # EN-Test erbt 'bestanden' aus der BITV-Quelle (kein Befund)
    assert by_id["EN_5_2_ACTIVATION"].result == "bestanden"
    assert by_id["EN_5_2_ACTIVATION"].en_kind == "verbindlich"
    # BITV-Kriterium hat kein en_kind (kein EN-Kriterium)
    assert by_id["BITV_5_2_AKTIVIERUNG_VON_BARRIEREFREIHEITSFUNKTIONEN"].en_kind is None


async def test_disabled_test_result_nicht_anwendbar(db_session):
    """Deaktivierter Test: result 'nicht_anwendbar', kein Einfluss aufs Urteil."""
    job_id = "job-en-disabled-result"
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done"))
    db_session.add_all([
        TestRecord(job_id=job_id, test_id="WCAG_1_1_1_IMG_ALT", title="Nicht-Text-Inhalte",
                   suite="bitv", level="MUSS", wcag_level="A", category="WCAG",
                   number="1.1.1", responsibility="redaktionell",
                   priority="hoch", type="syntax", status="implemented"),
        TestRecord(job_id=job_id, test_id="WCAG_2_1_1_KEYBOARD", title="Tastatur",
                   suite="bitv", level="MUSS", wcag_level="A", category="WCAG",
                   number="2.1.1", responsibility="technisch",
                   priority="hoch", type="resolution", status="nicht_relevant"),
    ])
    db_session.add(Page(job_id=job_id, url="https://example.com/", http_status=200, ok=True))
    db_session.commit()

    results = await build_results(job_id)
    by_id = {t.test_id: t for t in results.tests}
    assert by_id["WCAG_2_1_1_KEYBOARD"].result == "nicht_anwendbar"
    assert by_id["WCAG_2_1_1_KEYBOARD"].en_kind == "verbindlich"
    assert by_id["WCAG_1_1_1_IMG_ALT"].result == "bestanden"
    # EN-Kapitel 9: nur der aktive WCAG-Test zählt (der deaktivierte nicht)
    en = next(s for s in results.system_bewertung if s.system == "EN 301 549")
    assert en.gesamt == 1
    assert en.bestanden == 1


async def test_manuell_mit_dropdown_bewertung_erscheint_in_manual_liste(db_session):
    """Manuelles Kriterium (BITV-6/7/11/12) mit Dropdown-Bewertung → erscheint in
    der 'manuell zu prüfen'-Liste; die Bewertung fließt in die System-Bewertung ein."""
    job_id = "job-manual-dropdown"
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done",
                       options={"manual_assessments": {
                           "BITV_6_1_AUDIOBANDBREITE_FUER_SPRACHE": "nicht_anwendbar"}}))
    db_session.add(TestRecord(
        job_id=job_id, test_id="BITV_6_1_AUDIOBANDBREITE_FUER_SPRACHE",
        title="Audiobandbreite für Sprache", suite="bitv", level="MUSS", wcag_level=None,
        category="BITV", number="6.1", responsibility="redaktionell",
        priority="mittel", type="syntax", status="manual",
    ))
    db_session.add(Page(job_id=job_id, url="https://example.com/", http_status=200, ok=True))
    db_session.commit()

    results = await build_results(job_id)
    assert results is not None
    manual_ids = {t.test_id for t in results.manual_tests}
    assert "BITV_6_1_AUDIOBANDBREITE_FUER_SPRACHE" in manual_ids
    # Dropdown-Bewertung 'nicht_anwendbar' zählt in der BITV-Bewertung als bestanden
    bitv = next(s for s in results.system_bewertung if s.system == "BITV")
    assert bitv.gesamt == 1
    assert bitv.bestanden == 1
    assert bitv.nicht_automatisiert == 0
