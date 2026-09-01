"""
Mini-Integrationstest: echter Scan einer lokalen HTML-Fixture durch den vollen
Stack (JobManager → run_job → Playwright-Crawler → Checks → Persistenz).

Markiert als ``integration`` (nur im Container lauffähig, dort sind die
Playwright-Browser installiert; W3C-Aufrufe sind via A11Y_W3C_VALIDATOR_MAX=0
in conftest deaktiviert). Start: ``docker compose run api pytest -m integration``
"""
from __future__ import annotations

import asyncio
import http.server
import socketserver
import threading
from pathlib import Path

import pytest

pytest.importorskip("playwright")  # S7: Modul ohne Playwright-Installation überspringen

from app.engine.job_manager import JobManager  # noqa: E402
from app.engine.results import build_results  # noqa: E402
from app.schemas import JobCreate  # noqa: E402

_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "site"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(_FIXTURE_DIR), **kwargs)

    def log_message(self, *args):  # Konsolen-Ausgabe der Fixtures stillhalten
        pass


@pytest.fixture
def local_server():
    """Startet einen HTTP-Server für die Fixture-Seiten auf 127.0.0.1."""
    with socketserver.TCPServer(("127.0.0.1", 0), _Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        port = httpd.server_address[1]
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            httpd.shutdown()
            thread.join(timeout=5)


async def _poll_done(manager: JobManager, job_id: str, timeout: float = 90.0):
    waited = 0.0
    while waited < timeout:
        out = await manager.get_job(job_id)
        if out.status in ("done", "failed"):
            return out
        await asyncio.sleep(0.5)
        waited += 0.5
    raise AssertionError(f"Job {job_id} wurde nicht fertig (Timeout {timeout}s)")


@pytest.mark.integration
async def test_full_scan_of_local_fixture(local_server):
    manager = JobManager(max_parallel=1)
    out = await manager.create_job(
        JobCreate(
            url=f"{local_server}/index.html",
            suite="bitv",
            max_pages=3,
        )
    )
    final = await _poll_done(manager, out.id)
    assert final.status == "done", f"Job fehlgeschlagen: {final.error}"

    results = await build_results(out.id)
    assert results is not None
    assert results.page_count >= 1

    test_ids = {t.test_id for t in results.by_test}

    # Bekannte Verstöße der Fixture-Startseite:
    # - <html> ohne lang → WCAG_3_1_1_LANG
    # - <img> ohne alt → WCAG_1_1_1_IMG_ALT
    # - toter Link → LINKS_404 (Pseudo-Test)
    for expected in ("WCAG_3_1_1_LANG", "WCAG_1_1_1_IMG_ALT", "LINKS_404"):
        assert expected in test_ids, f"{expected} nicht gefunden (hat: {sorted(test_ids)})"

    # Pseudo-Test trägt den lesbaren Titel
    links404 = next(t for t in results.by_test if t.test_id == "LINKS_404")
    assert links404.title == "Tote Links (404)"
    assert links404.urls  # mindestens eine Fundseite

    # Die interne Folge-Seite sollte gecrawlt worden sein
    urls = {u.url for u in results.by_url}
    assert f"{local_server}/index.html" in urls
