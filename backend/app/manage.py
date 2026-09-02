"""
Verwaltungs-CLI für App-Logins — es gibt KEINEN Registrierungsweg im Frontend,
Zugänge legt ausschließlich der Betreiber hiermit an.

Beispiele (im api-Container, von /app):
    docker compose run --rm api python -m app.manage users list
    docker compose run --rm api python -m app.manage users add max --password '…'
    docker compose run --rm api python -m app.manage users add max   # interaktiv
    docker compose run --rm api python -m app.manage users set-password max
    docker compose run --rm api python -m app.manage users remove max --yes

Ohne ``--password`` wird interaktiv nachgefragt (getpass); das funktioniert mit
``docker compose run -it``. Bewusst nur leichtgewichtige Imports (DB/Config/
security), damit der Aufruf ohne Playwright-/Engine-Initialisierung schnell ist.
"""
from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import func, select

# Imports nach sys.path-Setup: das Modul wird als `python -m app.manage` aus
# dem Backend-Root (Container /app) ausgeführt.
from app.db import SessionLocal, init_db  # noqa: E402
from app.models import User, WsToken  # noqa: E402
from app.security import _MAX_PASSWORD_BYTES, hash_password  # noqa: E402

_MAX_USERNAME_LEN = 64


def _norm_username(raw: str) -> str:
    return raw.strip()


def _find_user(session, username: str) -> User | None:
    return session.execute(
        select(User).where(func.lower(User.username) == username.lower())
    ).scalar_one_or_none()


def _cmd_users_add(args: argparse.Namespace) -> int:
    username = _norm_username(args.username)
    if not username:
        print("Fehler: Benutzername darf nicht leer sein.", file=sys.stderr)
        return 2
    if len(username) > _MAX_USERNAME_LEN:
        print(f"Fehler: Benutzername darf höchstens {_MAX_USERNAME_LEN} Zeichen haben.", file=sys.stderr)
        return 2

    with SessionLocal() as session:
        if _find_user(session, username) is not None:
            print(f"Fehler: Benutzer '{username}' existiert bereits.", file=sys.stderr)
            return 2
        password = _read_password(args)
        if password is None:
            return 2
        session.add(User(username=username, password_hash=hash_password(password)))
        session.commit()
    print(f"Benutzer '{username}' angelegt.")
    return 0


def _cmd_users_set_password(args: argparse.Namespace) -> int:
    username = _norm_username(args.username)
    with SessionLocal() as session:
        user = _find_user(session, username)
        if user is None:
            print(f"Fehler: Benutzer '{username}' nicht gefunden.", file=sys.stderr)
            return 2
        password = _read_password(args)
        if password is None:
            return 2
        user.password_hash = hash_password(password)
        session.commit()
    print(f"Passwort für '{username}' aktualisiert.")
    return 0


def _cmd_users_list(_args: argparse.Namespace) -> int:
    with SessionLocal() as session:
        users = session.execute(
            select(User).order_by(User.username)
        ).scalars().all()
    if not users:
        print("Keine Benutzer angelegt.")
        return 0
    for u in users:
        print(f"{u.id}\t{u.username}\t{u.created_at.isoformat()}")
    return 0


def _cmd_users_remove(args: argparse.Namespace) -> int:
    if not args.yes:
        print("Sicher? Angabe '--yes' zum Löschen erforderlich.", file=sys.stderr)
        return 2
    username = _norm_username(args.username)
    with SessionLocal() as session:
        user = _find_user(session, username)
        if user is None:
            print(f"Fehler: Benutzer '{username}' nicht gefunden.", file=sys.stderr)
            return 2
        # Sessions des Benutzers werden über cascade="all, delete-orphan"
        # mitgelöscht; lose WS-Tickets räumen wir explizit mit auf.
        session.query(WsToken).filter(WsToken.user_id == user.id).delete()
        session.delete(user)
        session.commit()
    print(f"Benutzer '{username}' entfernt.")
    return 0


def _read_password(args: argparse.Namespace) -> str | None:
    """Passwort aus --password oder interaktiv (getpass) lesen und validieren."""
    if args.password:
        password = args.password
    else:
        password = getpass.getpass("Passwort: ")
        if not password:
            print("Fehler: Passwort darf nicht leer sein.", file=sys.stderr)
            return None
        password2 = getpass.getpass("Passwort wiederholen: ")
        if password != password2:
            print("Fehler: Passwörter stimmen nicht überein.", file=sys.stderr)
            return None
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        print(
            f"Fehler: Passwort darf höchstens {_MAX_PASSWORD_BYTES} Bytes haben.",
            file=sys.stderr,
        )
        return None
    return password


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.manage",
        description="Verwaltung der App-Logins (kein Registrierungsweg).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    users = sub.add_parser("users", help="Benutzer verwalten")
    users_sub = users.add_subparsers(dest="action", required=True)

    add = users_sub.add_parser("add", help="Benutzer anlegen")
    add.add_argument("username")
    add.add_argument("--password", help="Passwort (sonst interaktiv)")
    add.set_defaults(func=_cmd_users_add)

    pw = users_sub.add_parser("set-password", help="Passwort setzen/zurücksetzen")
    pw.add_argument("username")
    pw.add_argument("--password", help="Passwort (sonst interaktiv)")
    pw.set_defaults(func=_cmd_users_set_password)

    lst = users_sub.add_parser("list", help="Benutzer auflisten")
    lst.set_defaults(func=_cmd_users_list)

    rm = users_sub.add_parser("remove", help="Benutzer löschen (Sessions mit)")
    rm.add_argument("username")
    rm.add_argument("--yes", action="store_true", help="Löschen bestätigen")
    rm.set_defaults(func=_cmd_users_remove)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    init_db()  # Tabellen anlegen, falls die App noch nie gestartet wurde
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
