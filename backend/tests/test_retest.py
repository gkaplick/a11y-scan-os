"""
Retest- und W3C-Positions-Tests:

- create_retest legt einen Mini-Job mit den richtigen Optionen an (retest,
  test_ids, Auflösung) — mit Fake-Runner, kein echtes Crawling.
- _dom_path_at_position leitet aus einer W3C-Zeilenangabe einen echten
  DOM-Pfad ab (statt einer reinen Zeilen-/Spaltenangabe).
"""
from __future__ import annotations

from bs4 import BeautifulSoup

import app.engine.job_manager as jm_module
from app.engine.checks import _helpers as w3c
from app.engine.job_manager import JobManager


# ------------------------------------------------------------- Retest-Anlage

async def test_create_retest_sets_mini_job_options(monkeypatch):
    async def fake_run(job_id):
        pass  # kein echter Scan in Unit-Tests

    monkeypatch.setattr(jm_module, "run_job", fake_run)
    manager = JobManager(max_parallel=1)

    out = await manager.create_retest(
        "https://example.com/", "WCAG_1_1_1_IMG_ALT", "bitv", resolution=320
    )
    assert out is not None
    assert out.url == "https://example.com/"
    assert out.suite == "bitv"
    assert out.status in {"queued", "running"}

    # Optionen müssen den schlanken Runner-Pfad aktivieren
    with jm_module.SessionLocal() as session:
        row = session.get(jm_module.Job, out.id)
    assert row is not None
    assert row.options.get("retest") is True
    assert row.options.get("test_ids") == ["WCAG_1_1_1_IMG_ALT"]
    assert row.options.get("resolutions") == [320]


async def test_create_retest_default_resolution(monkeypatch):
    async def fake_run(job_id):
        pass

    monkeypatch.setattr(jm_module, "run_job", fake_run)
    manager = JobManager(max_parallel=1)

    out = await manager.create_retest("https://example.com/", "WCAG_1_1_1_IMG_ALT", "all", None)
    with jm_module.SessionLocal() as session:
        row = session.get(jm_module.Job, out.id)
    assert row.options["resolutions"] == [320, 1920]


# ------------------------------------------------------ W3C-Position → DOM-Pfad

_HTML = """<html><head><title>Test</title></head><body>
<main>
  <section>
    <h1>Überschrift</h1>
    <img src="bild.jpg" alt="Beschreibung">
    <p>Ein Absatz mit Text.</p>
  </section>
</main>
</body></html>"""


def test_dom_path_at_position_finds_img():
    soup = BeautifulSoup(_HTML, "html.parser")
    html_str = str(soup)  # Produktions-Serialisierung (nicht prettify)
    # Zeile der <img>-Zeile in der str()-Serialisierung ermitteln
    lines = html_str.splitlines()
    img_line = next(i + 1 for i, l in enumerate(lines) if "<img" in l)
    path = w3c._dom_path_at_position(soup, html_str, img_line)
    assert path == "body > main > section > img"


def test_dom_path_at_position_unknown_line_returns_empty():
    soup = BeautifulSoup(_HTML, "html.parser")
    html_str = str(soup)
    assert w3c._dom_path_at_position(soup, html_str, 9999) == ""
    assert w3c._dom_path_at_position(soup, "", 1) == ""
