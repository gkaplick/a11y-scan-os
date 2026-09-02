"""
Authentifizierung des a11y-Scanners (App-Login, kein Registrierungsweg).

Prinzip:
- Passwörter werden mit bcrypt gehasht (Cost 12). bcrypt blockiert ~100–300 ms
  CPU → Aufrufe im async-Kontext laufen über ``asyncio.to_thread``.
- Sessions sind opake Zufalls-Tokens in einem ``httpOnly``-Cookie. In der DB
  liegt nur der SHA-256-Hash (``digest``), nie das Token selbst.
- Für den WebSocket-Live-Progress gibt es separat kurzlebige Einmal-Tickets
  (``WsToken``): Der Nitro-WS-Tunnel kann Cookies nicht ans Backend
  weiterreichen, also holt die SPA das Ticket über die (Cookie-)Session und
  hängt es als ``?ws_token=…`` an.

Alle DB-Zugriffe sind sync und werden als ``_do()``-Closure über
``asyncio.to_thread`` ausgeführt (Muster wie in engine/job_manager.py).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, Request, Response
from sqlalchemy import delete, select

from .config import settings
from .db import SessionLocal
from .models import AuthSession, User, WsToken

# bcrypt verarbeitet höchstens 72 Bytes — länger wird stillschweigend gekürzt
# (Versionenabhängig auch mit Warnung). Zum Login-Zeitpunkt geben wir deshalb
# schlicht False zurück, statt einen Fehler zu werfen.
_MAX_PASSWORD_BYTES = 72

_BCRYPT_ROUNDS = 12

# Dummy-Hash für den "User existiert nicht"-Fall: gleiche Rechenzeit wie ein
# echter Verify, damit die Antwortzeit keinen Username verrät (Enumeration).
# Als str (wie DB-Hashes), damit verify_password einheitlich encode kann.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-bcrypt-vergleich", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("ascii")


def hash_password(password: str) -> str:
    """Hasht ein Klartext-Passwort (bcrypt). Wirft bei >72 Bytes."""
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        raise ValueError("Passwort zu lang (max. 72 Bytes)")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, password_hash: str | bytes) -> bool:
    """Prüft ein Passwort gegen einen bcrypt-Hash. Zu lang → False (kein 500)."""
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        return False
    try:
        hashed = password_hash if isinstance(password_hash, bytes) else password_hash.encode("ascii")
        return bcrypt.checkpw(password.encode("utf-8"), hashed)
    except ValueError:
        return False


def new_token() -> str:
    """Opaker Zufalls-Token (URL-safe, 32 Bytes Entropie)."""
    return secrets.token_urlsafe(32)


def digest(token: str) -> str:
    """SHA-256-Hex — nur dieser Hash wird in der DB gespeichert."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    """SQLite liefert DateTime(timezone=True) als naive Werte zurück — für den
    Python-Vergleich die UTC-Zone ergänzen, falls fehlend."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


# --- Cookies ---------------------------------------------------------------


def set_session_cookie(response: Response, raw_token: str) -> None:
    """Setzt das Session-Cookie (httpOnly, SameSite=Lax, Secure per Settings)."""
    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        max_age=int(settings.session_ttl_hours * 3600),
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )


def clear_session_cookie(response: Response) -> None:
    """Löscht das Session-Cookie im Browser."""
    response.delete_cookie(settings.session_cookie_name, path="/")


def session_token_from_request(request: Request) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


# --- Sessions --------------------------------------------------------------


def _issue_session(user: User) -> str:
    """Legt eine Session an und liefert das rohe Token (nur Hash landet in der DB)."""
    raw = new_token()
    expires_at = _now() + timedelta(hours=settings.session_ttl_hours)
    with SessionLocal() as session:
        # Opportunistisch verfallene Sitzungen aufräumen.
        session.execute(delete(AuthSession).where(AuthSession.expires_at <= _now()))
        session.add(AuthSession(token_hash=digest(raw), user_id=user.id, expires_at=expires_at))
        session.commit()
    return raw


def _validate_session(raw_token: str) -> User | None:
    if not raw_token:
        return None
    with SessionLocal() as session:
        row = session.execute(
            select(AuthSession).where(AuthSession.token_hash == digest(raw_token))
        ).scalar_one_or_none()
        if row is None:
            return None
        if _ensure_aware(row.expires_at) <= _now():
            session.delete(row)
            session.commit()
            return None
        # Sliding: Ablauf bei Benutzung verlängern.
        row.expires_at = _now() + timedelta(hours=settings.session_ttl_hours)
        session.commit()
        user = session.get(User, row.user_id)
    return user


def _delete_session(raw_token: str) -> None:
    if not raw_token:
        return
    with SessionLocal() as session:
        row = session.execute(
            select(AuthSession).where(AuthSession.token_hash == digest(raw_token))
        ).scalar_one_or_none()
        if row is not None:
            session.delete(row)
            session.commit()


async def issue_session(user: User) -> str:
    return await asyncio.to_thread(_issue_session, user)


async def validate_session(raw_token: str) -> User | None:
    return await asyncio.to_thread(_validate_session, raw_token)


async def delete_session(raw_token: str) -> None:
    await asyncio.to_thread(_delete_session, raw_token)


async def require_user(request: Request) -> User:
    """FastAPI-Dependency: gültiges Session-Cookie → User, sonst 401."""
    token = session_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Nicht angemeldet")
    user = await validate_session(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Nicht angemeldet")
    return user


# --- WS-Tickets ------------------------------------------------------------


def _issue_ws_token(user_id: int) -> str:
    raw = new_token()
    expires_at = _now() + timedelta(seconds=settings.ws_token_ttl_seconds)
    with SessionLocal() as session:
        session.execute(delete(WsToken).where(WsToken.expires_at <= _now()))
        session.add(WsToken(token_hash=digest(raw), user_id=user_id, expires_at=expires_at))
        session.commit()
    return raw


def _consume_ws_token(raw_token: str) -> User | None:
    """Validiert ein WS-Ticket und verbraucht es (Einmal-Ticket)."""
    if not raw_token:
        return None
    with SessionLocal() as session:
        row = session.execute(
            select(WsToken).where(WsToken.token_hash == digest(raw_token))
        ).scalar_one_or_none()
        if row is None or _ensure_aware(row.expires_at) <= _now():
            return None
        session.delete(row)  # Einmal-Ticket: nach Gebrauch ungültig
        session.commit()
        return session.get(User, row.user_id)


async def issue_ws_token(user_id: int) -> str:
    return await asyncio.to_thread(_issue_ws_token, user_id)


async def consume_ws_token(raw_token: str) -> User | None:
    return await asyncio.to_thread(_consume_ws_token, raw_token)


def verify_dummy(password: str) -> None:
    """Verbrennt einen bcrypt-Vergleich gegen einen Dummy-Hash.

    Wird beim Login für unbekannte Benutzernamen ausgeführt, damit die
    Antwortzeit keinen Rückschluss zulässt (Anti-Enumeration). Der Rückgabe-
    wert wird ignoriert — auch ein "echter" Treffer landet danach im 401.
    """
    verify_password(password, _DUMMY_HASH)


# --- Admin-Bootstrap --------------------------------------------------------


def _ensure_admin() -> bool:
    """Legt beim ersten Start den Admin aus A11Y_ADMIN_USERNAME/-PASSWORD an.

    Nur wenn die users-Tabelle leer ist und beide Credentials gesetzt sind —
    sonst Warnung loggen (Zugänge dann nur über die Verwaltungs-CLI).
    """
    logger = logging.getLogger(__name__)
    username = settings.admin_username.strip()
    password = settings.admin_password

    with SessionLocal() as session:
        if session.scalar(select(User.id).limit(1)) is not None:
            return False
        if not username or not password:
            logger.warning(
                "users-Tabelle leer und A11Y_ADMIN_USERNAME/-PASSWORD nicht "
                "gesetzt — Zugänge über `python -m app.manage users add …` anlegen."
            )
            return False
        if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
            logger.error(
                "A11Y_ADMIN_PASSWORD ist länger als %s Bytes — Admin wird NICHT "
                "angelegt. Kürzeres Passwort setzen oder Zugang per CLI anlegen.",
                _MAX_PASSWORD_BYTES,
            )
            return False
        session.add(User(username=username, password_hash=hash_password(password)))
        session.commit()
    logger.info("Admin-Benutzer '%s' angelegt.", username)
    return True


async def ensure_admin() -> bool:
    return await asyncio.to_thread(_ensure_admin)
