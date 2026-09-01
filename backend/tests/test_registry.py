"""
Registry-Integritätstests — die Grundlage dafür, dass die App zur Reife kommt:

- alle test_ids eindeutig und konsistent (validate_registry -> keine Warnungen)
- jede nicht-manuelle Check-Funktion existiert (get_check / CHECK_FUNCTIONS)
- Stub-Checks werfen deterministisch CheckNotImplemented
- Suiten- und Typ-Aufteilungen sind konsistent
"""
from __future__ import annotations

from bs4 import BeautifulSoup
import pytest

from app.engine import registry as reg
from app.engine.checks import CHECK_FUNCTIONS, MISSING_CHECKS, CheckNotImplemented, get_check
from app.engine.checks._base import CheckContext

_SIMPLE_HTML = "<html><head><title>T</title></head><body><p>Hallo</p></body></html>"


def _ctx(test_id: str) -> CheckContext:
    return CheckContext(
        url="https://example.com/",
        soup=BeautifulSoup(_SIMPLE_HTML, "html.parser"),
        test_id=test_id,
        # Keine externen W3C-Validator-Aufrufe in Unit-Tests
        w3c_enabled=False,
    )


# ---------------------------------------------------------------- Grunddaten

def test_no_duplicate_test_ids():
    ids = [e["test_id"] for e in reg.REGISTRY]
    assert len(ids) == len(set(ids))


def test_get_test_index_complete():
    """get_test()/BY_ID müssen ALLE Registry-Einträge auflösen.

    Der Index wird erst NACH `REGISTRY += BITV_STEPS` gebaut — sonst fehlen die
    98 bitv_steps-Einträge in BY_TEST_ID und get_test() liefert für alle
    bitv_-Tests None (kaputtes id/description in Ergebnissen, Retest-404).
    """
    assert set(reg.BY_TEST_ID) == {e["test_id"] for e in reg.REGISTRY}
    assert all(reg.get_test(e["test_id"]) is not None for e in reg.REGISTRY)
    assert set(reg.BY_ID) == {e["id"] for e in reg.REGISTRY}


def test_validate_registry_clean():
    assert reg.validate_registry() == []


def test_all_entries_have_required_fields():
    required = {"id", "test_id", "title", "suite", "level", "wcag_level", "category",
                "responsibility", "priority", "type",
                "module", "check", "status", "description", "solution", "test_hint"}
    for e in reg.REGISTRY:
        missing = required - set(e)
        assert not missing, f"{e['test_id']}: fehlende Felder {sorted(missing)}"


def test_no_cross_reference_fields():
    """Keine Querweise: kein Eintrag referenziert Nummern anderer Systeme."""
    for e in reg.REGISTRY:
        assert "wcag" not in e, f"{e['test_id']}: unerlaubtes Feld 'wcag'"
        assert "bitv" not in e, f"{e['test_id']}: unerlaubtes Feld 'bitv'"
        assert "en301549" not in e, f"{e['test_id']}: unerlaubtes Feld 'en301549'"


def test_system_partition():
    """Die drei Test-Systeme sind vollständig getrennt (Kategorie-Aufteilung)."""
    counts = {}
    for e in reg.REGISTRY:
        counts[e["category"]] = counts.get(e["category"], 0) + 1
    assert counts == {"BITV": 102, "WCAG": 93, "EN 301 549": 41}
    assert len(reg.REGISTRY) == 236


def test_system_file_prefixes():
    """Je Eintrag: Datei-Präfix = System-Präfix (bitv_/wcag_/en_), module konsistent."""
    prefix_by_category = {"BITV": "bitv_", "WCAG": "wcag_", "EN 301 549": "en_"}
    for e in reg.REGISTRY:
        prefix = prefix_by_category[e["category"]]
        assert e["test_id"].lower().startswith(prefix), (
            f"{e['test_id']} (Kategorie {e['category']}): Präfix {prefix} erwartet"
        )
        # Manuelle Kriterien haben kein Modul (module=None nach der Stub-Umstellung).
        if e["module"] is not None:
            assert e["module"] == e["test_id"].lower()


def test_module_field_equals_test_id_lower():
    """Eine Datei pro Test: module = test_id.lower() hält die Trennung wcag_/en_/bitv_."""
    for e in reg.REGISTRY:
        if e["module"] is None:   # manuelle Kriterien (keine Check-Datei)
            continue
        assert e["module"] == e["test_id"].lower(), (
            f"{e['test_id']}: module={e['module']!r} != test_id.lower()"
        )


# ------------------------------------------------------------- Check-Auflösung

def test_no_missing_checks():
    assert MISSING_CHECKS == []


def test_every_non_manual_test_has_resolvable_check():
    for e in reg.REGISTRY:
        if e["status"] == "manual":
            continue
        assert e["check"], f"{e['test_id']}: status={e['status']} ohne check-Funktion"
        assert e["test_id"] in CHECK_FUNCTIONS, f"{e['test_id']} nicht registriert"


# ------------------------------------------------- Es gibt keine Stubs mehr

def test_no_stubs_remain():
    """Die Stub-Kategorie ist abgeschafft (User-Vorgabe): jedes Kriterium ist
    entweder automatisiert (implemented) oder manuell (manual). Die Stub->
    manual-Umstellung in engine/checks/__init__.py hinterlässt keinen einzigen
    Stub-Eintrag."""
    stub_entries = [e for e in reg.REGISTRY if e["status"] == "stub"]
    assert stub_entries == []
    assert reg.get_stub_test_ids("all") == []


def test_status_derived_from_check_source():
    """Der Registry-status ist aus dem Check-Code abgeleitet (kein Hand-Pflegen).

    checks/__init__ setzt status automatisch: implemented ⇔ registrierte
    Check-Funktion ohne ``raise CheckNotImplemented``, sonst stub. Manuelle
    Kriterien (type=manual) bleiben manuell. Ein Check gilt also genau dann
    als implementiert, wenn sein Modul einen echten Algorithmus enthält —
    das Frontend zeigt damit immer den Code-Stand, ohne Status-Feld-Pflege.
    """
    from app.engine.checks import _ist_stub_check, CHECK_FUNCTIONS, effective_status

    for e in reg.REGISTRY:
        if e["type"] == "manual":
            assert e["status"] == "manual", e["test_id"]
            assert effective_status(e["test_id"]) == "manual"
            continue
        fn = CHECK_FUNCTIONS.get(e["test_id"])
        expected = "implemented" if fn is not None and not _ist_stub_check(fn) else "stub"
        assert e["status"] == expected, (
            f"{e['test_id']}: Registry-status {e['status']!r} != abgeleitet {expected!r}"
        )
        assert effective_status(e["test_id"]) == expected


@pytest.mark.parametrize("entry", [e for e in reg.REGISTRY if e["status"] == "stub"],
                         ids=lambda e: e["test_id"])
async def test_stub_raises_check_not_implemented(entry):
    fn = get_check(entry["test_id"])
    with pytest.raises(CheckNotImplemented):
        await fn(_ctx(entry["test_id"]))


# ------------------------------------------------------------- Implementiert

@pytest.mark.parametrize(
    "entry",
    # Nur Syntax-Checks: Resolution-Checks brauchen eine echte Playwright-Seite
    # (ctx.page) — die sind im Integrationstest gegen die lokale Fixture abgedeckt.
    [e for e in reg.REGISTRY if e["status"] == "implemented" and e["type"] == "syntax"],
    ids=lambda e: e["test_id"],
)
async def test_implemented_check_runs_without_crash(entry):
    """Implementierte Syntax-Checks dürfen nicht abstürzen (auch nicht bei leerer Seite).

    Returnwert ist ein list[Finding] (oder leer). Ein Absturz wäre ein Bug —
    er würde im Runner still geschluckt und der Test als 'stub' verbucht.
    """
    fn = get_check(entry["test_id"])
    try:
        result = await fn(_ctx(entry["test_id"]))
    except CheckNotImplemented:
        pytest.fail(f"{entry['test_id']}: als implemented registriert, wirft aber CheckNotImplemented")
    assert isinstance(result, list)


# ------------------------------------------------------------------- Suiten

def test_suite_partition_is_complete():
    bitv = reg.get_tests_for_suite("bitv")
    extra = reg.get_tests_for_suite("wcag")
    assert len(reg.REGISTRY) == len(bitv) + len(extra)
    bitv_ids = {e["test_id"] for e in bitv}
    extra_ids = {e["test_id"] for e in extra}
    assert bitv_ids | extra_ids == {e["test_id"] for e in reg.REGISTRY}
    assert bitv_ids & extra_ids == set()


def test_suite_all_matches_everything():
    assert len(reg.get_tests_for_suite("all")) == len(reg.REGISTRY)


def test_level_distribution_is_sane():
    """BITV-MUSS/SOLLTE/KANN — es darf keine leere Kategorie geben."""
    levels = {}
    for e in reg.REGISTRY:
        levels[e["level"]] = levels.get(e["level"], 0) + 1
    for level in ("MUSS", "SOLLTE", "KANN"):
        assert levels.get(level, 0) > 0, f"Level {level} komplett unbesetzt"
