"""
Integrationstest: Die Test-Website (testwebsite/) erfüllt ihren Zweck.

Je Kriterium (aus ``site/catalog.json``, von ``testwebsite/generate.py``
geschrieben) gibt es zwei Seiten:
- ``<slug>-negativ.html``  → MUSS alle zugehörigen test_ids feuern
- ``<slug>-positiv.html``  → MUSS frei von den zugehörigen test_ids bleiben

Die Wahrheitsquelle ist ``site/catalog.json`` und NICHT ein Import von
``testwebsite/generate.py``: Im Container liegt nur ``site/`` (Dockerfile.api-
COPY nach /app/testwebsite), der Generator selbst nicht. Der Pfad ist sowohl
lokal (Projekt-Root/testwebsite/site) als auch im Container (/app/testwebsite)
aus ``Path(__file__).parent.parent.parent`` ableitbar.

Übersprungen werden Kriterien mit ``pytest: False`` (nur ``html-syntax``) —
die feuern über den W3C-Validator, der in Tests deaktiviert
(A11Y_W3C_VALIDATOR_MAX=0) und netzabhängig ist.

Markiert als ``integration`` (braucht Playwright + Browser, nur im Container
verfügbar). Laufzeit des Gesamt-Scans: ~2 h (Resolution-Checks iterieren je
Element per Playwright, s. ``_TIMEOUT_SCAN``).
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

pytest.importorskip("playwright")  # Modul ohne Playwright-Browser überspringen

from app.engine.job_manager import JobManager  # noqa: E402
from app.engine.results import build_results  # noqa: E402
from app.schemas import JobCreate  # noqa: E402


def _testwebsite_dir() -> Path:
    """Pfad zur generierten Test-Website (testwebsite/site/).

    Lokal: Projekt-Root/testwebsite/site; im Container: /app/testwebsite/site
    (Dockerfile.api-COPY). Aufwärts-Suche ab dem Test-Ordner findet beide —
    identische Logik wie ``_testwebsite_dir`` in conftest.py (dort nicht
    importierbar, weil tests/ ein Paket ist). Optional per A11Y_TESTWEBSITE_DIR
    übersteuerbar.
    """
    env = os.environ.get("A11Y_TESTWEBSITE_DIR")
    if env:
        return Path(env)
    current = Path(__file__).resolve().parent  # backend/tests bzw. /app/tests
    while current != current.parent:
        site = current / "testwebsite" / "site"
        if (site / "catalog.json").is_file():
            return site
        current = current.parent
    return Path(__file__).parent.parent.parent / "testwebsite" / "site"


_CATALOG_PATH = _testwebsite_dir() / "catalog.json"


def _lade_katalog() -> list[dict]:
    """Liest die Katalog-Wahrheitsquelle (site/catalog.json)."""
    if not _CATALOG_PATH.is_file():
        pytest.skip(f"catalog.json fehlt: {_CATALOG_PATH} — bitte testwebsite/generate.py ausführen")
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


# Der Voll-Scan über ~165 Seiten × 2 Auflösungen dauert mit den aktuell
# implementierten Resolution-Checks (Kontrast- und Fokus-Prüfungen iterieren je
# Element per Playwright) ~2 Stunden — siehe Profiling:
# _deepest_text_elements + Effektiv-Farben ≈ 6 Playwright-Roundtrips/Element,
# Fokus-Checks ≈ 250 ms/Element. Das Timeout muss dem Rechnung tragen.
_TIMEOUT_SCAN = 9000.0  # 2,5 h — Voll-Scan inkl. index.html (große Hub-Seite)


async def _poll_done(manager: JobManager, job_id: str, timeout: float = _TIMEOUT_SCAN):
    waited = 0.0
    while waited < timeout:
        out = await manager.get_job(job_id)
        if out.status in ("done", "failed"):
            return out
        await asyncio.sleep(0.5)
        waited += 0.5
    # Job sauber abbrechen, damit beim Teardown kein laufender asyncio-Task
    # mit unklarem Status zurückbleibt (Runner setzt status="canceled").
    await manager.cancel_job(job_id)
    raise AssertionError(f"Job {job_id} wurde nicht fertig (Timeout {timeout}s)")


@pytest.fixture(scope="module")
async def scan(testwebsite_server):
    """Ein Gesamt-Scan über die Test-Website; Ergebnisse je Modul einmalig.

    Liefert (results, server_base, katalog) — die Kriterienliste ist bereits
    auf die per pytest prüfbaren (``pytest: True``) gefiltert.
    """
    katalog = _lade_katalog()
    pruefbar = [k for k in katalog if k.get("pytest", True)]
    assert pruefbar, "Katalog enthält keine prüfbaren Kriterien"

    manager = JobManager(max_parallel=1)
    out = await manager.create_job(
        JobCreate(
            url=f"{testwebsite_server}/index.html",
            suite="all",
            max_pages=250,
            # Beide Auflösungen sind nötig: viewport-sensitive Checks sind hart
            # auf schmale/breite Viewports gated — WCAG_1_4_10_REFLOW und die
            # Überlauf-Branch von BITV_9_1_4_10_INHALTE_BRECHEN_UM laufen nur
            # bei ≤ 768 px, WCAG_1_4_4_RESIZE nur bei > 1000 px. Der Slug
            # reflow-320-negativ verlangt explizit beide test_ids (dort 320 px
            # nötig); ohne 320er-Pass wäre der Test unvollständig. Die
            # desktop_only-Fokus-/Tastatur-Checks feuern ohnehin nur
            # > keyboard_min_width (1160 px).
            resolutions=[320, 1920],
        )
    )
    final = await _poll_done(manager, out.id)
    assert final.status == "done", f"Job fehlgeschlagen: {final.error}"

    results = await build_results(out.id)
    assert results is not None, "build_results lieferte None"
    return results, testwebsite_server, pruefbar


def _befunde_je_seite(results, server_base: str, slug: str, art: str) -> set[str]:
    """Set der test_ids, die auf der Seite ``<slug>-<art>.html`` feuern."""
    url = f"{server_base}/kriterien/{slug}-{art}.html"
    for eintrag in results.by_url:
        if eintrag.url == url:
            return {f.test_id for f in eintrag.findings}
    return set()  # Seite nicht gecrawlt → keine Befunde (wird unten als Fehlschlag gewertet)


@pytest.mark.integration
def test_negativ_seiten_feuern_erwartete_test_ids(scan):
    """Jede Negativ-Seite feuert (mindestens) alle ihre test_ids."""
    results, server_base, katalog = scan
    abweichungen: list[str] = []
    for k in katalog:
        slug = k["slug"]
        erwartet = set(k["test_ids"])
        gefunden = _befunde_je_seite(results, server_base, slug, "negativ")
        fehlend = erwartet - gefunden
        if fehlend:
            abweichungen.append(
                f"{slug}-negativ: fehlend {sorted(fehlend)} — Seite fehlt im Scan oder "
                f"Check feuert nicht (hat: {sorted(gefunden)})"
            )
    assert not abweichungen, (
        f"{len(abweichungen)} Negativ-Seiten feuern nicht ihre test_ids:\n"
        + "\n".join(abweichungen)
    )


@pytest.mark.integration
def test_positiv_seiten_bleiben_frei_von_test_ids(scan):
    """Jede Positiv-Seite bleibt frei von ihren test_ids (keine False-Positives)."""
    results, server_base, katalog = scan
    verstoesse: list[str] = []
    for k in katalog:
        slug = k["slug"]
        erwartet = set(k["test_ids"])
        gefunden = _befunde_je_seite(results, server_base, slug, "positiv")
        unerwartet = gefunden & erwartet
        if unerwartet:
            verstoesse.append(f"{slug}-positiv: unerwartete Befunde {sorted(unerwartet)}")
    assert not verstoesse, (
        f"{len(verstoesse)} Positiv-Seiten sind nicht sauber:\n" + "\n".join(verstoesse)
    )
