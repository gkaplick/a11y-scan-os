"""
HTTP-Tests für Login/Session/WS-Ticket.

Es gibt keinen Registrierungsweg — getestet werden der Login, der Schutz der
geschützten Routen, das Widerrufen via Logout sowie die kurzlebigen
WebSocket-Tickets. Der Admin-Env-Bootstrap wird separat geprüft.

Hinweis: ``TestClient(app)`` wird bewusst OHNE ``with``-Block genutzt, damit
der Lifespan (Admin-Bootstrap, Playwright-Warmstart) nicht läuft.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.models import User
from app.security import (
    _ensure_admin,
    consume_ws_token,
    hash_password,
    issue_ws_token,
    verify_password,
)

PASSWORD = "sicheres-passwort-123"


def _seed_user(username: str = "admin") -> int:
    with SessionLocal() as session:
        user = User(username=username, password_hash=hash_password(PASSWORD))
        session.add(user)
        session.commit()
        return user.id


def _login(client: TestClient, username: str = "admin", password: str = PASSWORD):
    return client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )


def test_geschuetzte_routen_ohne_session():
    """Alle geschützten Endpoints antworten ohne Session-Cookie mit 401."""
    client = TestClient(app)
    assert client.get("/api/jobs").status_code == 401
    assert client.get("/api/tests").status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/ws-token").status_code == 401
    # /api/health bleibt bewusst offen (Betrieb/Orchestrierung)
    assert client.get("/api/health").status_code == 200


def test_login_falsch_generisch_ohne_enumeration():
    _seed_user()
    client = TestClient(app)

    wrong = _login(client, password="falsches-passwort")
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "Ungültige Zugangsdaten."

    # Unbekannter Benutzername → identische Meldung (keine Enumeration).
    unknown = _login(client, username="gibts-nicht")
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == "Ungültige Zugangsdaten."


def test_login_me_und_geschuetzte_routen():
    _seed_user()
    client = TestClient(app)

    login = _login(client)
    assert login.status_code == 200
    assert login.json()["username"] == "admin"
    assert "a11y_session" in login.cookies  # Session-Cookie gesetzt

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == "admin"

    # Session gilt für die geschützten Router.
    assert client.get("/api/jobs").status_code == 200
    assert client.get("/api/tests").status_code == 200


def test_logout_widerruft_session():
    _seed_user()
    client = TestClient(app)
    assert _login(client).status_code == 200
    assert client.get("/api/auth/me").status_code == 200

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204
    # Session ist widerrufen — auch mit (altem) Cookie kein Zugriff mehr.
    assert client.get("/api/auth/me").status_code == 401


def test_ws_token_nur_mit_session():
    _seed_user()
    client = TestClient(app)
    assert client.get("/api/auth/ws-token").status_code == 401

    assert _login(client).status_code == 200
    resp = client.get("/api/auth/ws-token")
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert body["expires_at"]


async def test_ws_token_ist_einmalverbrauch():
    user_id = _seed_user("wsuser")
    raw = await issue_ws_token(user_id)

    user = await consume_ws_token(raw)
    assert user is not None and user.id == user_id
    # Zweiter Konsum desselben Tickets → verbraucht.
    assert await consume_ws_token(raw) is None
    # Unbekanntes Ticket → None.
    assert await consume_ws_token("unbekannt") is None


def test_admin_bootstrap_nur_wenn_users_leer_und_creds_gesetzt():
    # users leer + keine Credentials → nichts anlegen (Warnung), False.
    assert _ensure_admin() is False

    settings.admin_username = "admin"
    settings.admin_password = "geheim-123"
    try:
        assert _ensure_admin() is True
        # users nicht mehr leer → kein zweiter Anlauf.
        assert _ensure_admin() is False

        with SessionLocal() as session:
            user = session.query(User).filter_by(username="admin").first()
            assert user is not None
            assert verify_password("geheim-123", user.password_hash)
    finally:
        settings.admin_username = ""
        settings.admin_password = ""
