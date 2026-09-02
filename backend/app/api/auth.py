"""
Auth-API: Login/Logout/me sowie kurzlebige WebSocket-Tickets.

- POST /api/auth/login       Login → Session-Cookie setzen (httpOnly)
- POST /api/auth/logout      Session widerrufen + Cookie leeren
- GET  /api/auth/me          Aktueller Nutzer (401 wenn nicht angemeldet)
- GET  /api/auth/ws-token    Einmal-Ticket für den WebSocket-Live-Progress

Es gibt bewusst **keinen** Registrierungsendpoint — Zugänge werden nur über
den Env-Admin-Bootstrap (main.py) bzw. die Verwaltungs-CLI angelegt
(``python -m app.manage users add …``).

Login-Härtung: generische Fehlermeldung (keine User-Enumeration), für
unbekannte Benutzernamen läuft ein Dummy-bcrypt-Vergleich (konstante Zeit)
und ein In-Memory-Limiter begrenzt Fehlversuche pro Client-IP.
"""
from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select

from ..config import settings
from ..db import SessionLocal
from ..models import User
from ..schemas import LoginRequest, UserOut, WsTokenResponse
from ..security import (
    clear_session_cookie,
    delete_session,
    issue_session,
    issue_ws_token,
    require_user,
    session_token_from_request,
    set_session_cookie,
    verify_dummy,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Konstanten des Login-Limiters (pro Client-IP, In-Memory).
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 900      # 15 Minuten
_LOCKOUT_SECONDS = 900


class _LoginLimiter:
    """Minimaler In-Memory-Fehlversuch-Zähler (uvicorn = ein Worker).

    Hinweis: Hinter dem Nitro-Proxy ist die Client-IP die des Web-Containers —
    der Limiter wirkt damit faktisch global. Für ein Single-Ops-Tool bewusst
    akzeptiert; ``X-Forwarded-For`` wird nicht vertraut.
    """

    def __init__(self) -> None:
        self._fails: dict[str, list[float]] = {}
        self._lock: threading.Lock = threading.Lock()

    def _recent_failures(self, key: str) -> list[float]:
        now = time.monotonic()
        fails = [t for t in self._fails.get(key, []) if now - t < _WINDOW_SECONDS]
        if fails:
            self._fails[key] = fails
        elif key in self._fails:
            del self._fails[key]
        return fails

    def check(self, key: str) -> None:
        with self._lock:
            if len(self._recent_failures(key)) >= _MAX_ATTEMPTS:
                raise HTTPException(
                    status_code=429,
                    detail="Zu viele Fehlversuche — bitte später erneut versuchen.",
                )

    def register_failure(self, key: str) -> None:
        with self._lock:
            self._fails[key] = self._recent_failures(key) + [time.monotonic()]

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


_limiter = _LoginLimiter()


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unbekannt"


def _find_user(username: str) -> User | None:
    """User case-insensitiv suchen (Login verträgt Groß-/Kleinschreibung)."""
    name = username.strip()
    with SessionLocal() as session:
        return session.execute(
            select(User).where(func.lower(User.username) == name.lower())
        ).scalar_one_or_none()


def _to_user_out(user: User) -> UserOut:
    return UserOut(id=user.id, username=user.username, created_at=user.created_at)


@router.post("/login", response_model=UserOut)
async def login(payload: LoginRequest, request: Request, response: Response) -> UserOut:
    """Login → UserOut + Session-Cookie. Falsche Daten → generischer 401."""
    key = _client_key(request)
    _limiter.check(key)

    user = await asyncio.to_thread(_find_user, payload.username)
    if user is None:
        # Dummy-bcrypt für konstante Antwortzeit (Anti-Enumeration).
        await asyncio.to_thread(verify_dummy, payload.password)
        _limiter.register_failure(key)
        raise HTTPException(status_code=401, detail="Ungültige Zugangsdaten.")

    ok = await asyncio.to_thread(verify_password, payload.password, user.password_hash)
    if not ok:
        _limiter.register_failure(key)
        raise HTTPException(status_code=401, detail="Ungültige Zugangsdaten.")

    _limiter.reset(key)
    raw = await issue_session(user)
    set_session_cookie(response, raw)
    return _to_user_out(user)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response) -> Response:
    """Widerruft die Session (sofort) und leert das Cookie."""
    token = session_token_from_request(request)
    if token:
        await delete_session(token)
    clear_session_cookie(response)
    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(require_user)) -> UserOut:
    return _to_user_out(user)


@router.get("/ws-token", response_model=WsTokenResponse)
async def ws_token(user: User = Depends(require_user)) -> WsTokenResponse:
    """Kurzlebiges Einmal-Ticket für den WebSocket-Live-Progress eines Jobs."""
    raw = await issue_ws_token(user.id)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.ws_token_ttl_seconds)
    return WsTokenResponse(token=raw, expires_at=expires_at)
