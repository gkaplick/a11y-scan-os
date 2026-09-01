"""
Pytest-Fixtures für den a11y-Scanner.

WICHTIG: Die A11Y_-Umgebungsvariablen werden VOR dem Import von ``app.*``
gesetzt, damit ``app.config.settings`` (pydantic-settings, liest Env beim
Instantieren) auf eine temporäre Datenbank und ein temporäres Ausgabeverzeichnis
zeigt. So laufen Tests isoliert von echten ``data/``- und ``docs/``-Daten.

- ``A11Y_DATABASE_PATH``      → temporäre SQLite-Datei
- ``A11Y_OUTPUT_DIR``         → temporäres Export-Verzeichnis
- ``A11Y_W3C_VALIDATOR_MAX=0``→ keine externen W3C-Validator-Aufrufe in Tests
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="a11y-test-")
os.environ["A11Y_DATABASE_PATH"] = os.path.join(_TMP, "test.db")
os.environ["A11Y_OUTPUT_DIR"] = os.path.join(_TMP, "reports")
os.environ["A11Y_SCREENSHOTS_DIR"] = os.path.join(_TMP, "screenshots")
os.environ["A11Y_W3C_VALIDATOR_MAX"] = "0"
os.environ["A11Y_DEBUG"] = "false"

import pytest  # noqa: E402  (Import nach Env-Setup ist Absicht)

from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Finding, Job, Page, TestRecord  # noqa: E402

init_db()


@pytest.fixture(autouse=True)
def _clean_db():
    """Leert alle Tabellen vor jedem Test (Kinder zuerst, FK-Reihenfolge)."""
    with SessionLocal() as session:
        session.query(Finding).delete()
        session.query(TestRecord).delete()
        session.query(Page).delete()
        session.query(Job).delete()
        session.commit()
    yield


@pytest.fixture
def db_session():
    """Offene Session für Fixture-Insertion in Tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _testwebsite_dir() -> Path:
    """Pfad zur generierten Test-Website (testwebsite/site/).

    Lokal: Projekt-Root/testwebsite/site.
    Im API-Container: /app/testwebsite (Dockerfile.api-COPY — dort liegt der
    Backend-Code unter /app, NICHT unter /app/backend; deshalb funktioniert
    ein fester Eltern-Pfad nicht in beiden Umgebungen).

    Lösung: Aufwärts-Suche vom backend/tests-Ordner nach
    ``testwebsite/site/catalog.json`` — identische Logik lokal und im
    Container. Optional per A11Y_TESTWEBSITE_DIR übersteuerbar.
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


@pytest.fixture(scope="module")
def testwebsite_server():
    """HTTP-Server für die generierte Test-Website (ephemerer Port).

    Modul-Scope, damit der Integrationstest (tests/test_testwebsite.py) einen
    einzigen Scan über die Site einmalig pro Modul ausführen kann.


    Analog zu ``local_server`` in tests/test_integration.py, aber für die
    im Generator gebaute Demo-/Test-Website. Übersprungen, wenn die Site
    nicht generiert wurde (testwebsite/generate.py ausführen).
    """
    import http.server
    import socketserver
    import threading

    directory = _testwebsite_dir()
    if not directory.is_dir():
        pytest.skip(f"Test-Website nicht gefunden: {directory} — bitte testwebsite/generate.py ausführen")

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, *args):  # Konsolen-Ausgabe stillhalten
            pass

    with socketserver.TCPServer(("127.0.0.1", 0), _Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        port = httpd.server_address[1]
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            httpd.shutdown()
            thread.join(timeout=5)
