"""
Check-Dispatch: baut aus dem Registry (engine/registry.py) die Zuordnung
test_id → Check-Funktion. Jeder Registry-Eintrag mit gesetztem ``check``
und ``module`` wird importiert und registriert; Auflösungsfehler landen in
MISSING_CHECKS (sichtbar für Tests/Report, statt still zu schweigen).

Kontrakt aller Checks:
    async def check_xxx(ctx: CheckContext) -> list[Finding]
Stub-Checks werfen ``CheckNotImplemented`` — der Runner verbucht sie als
"stub" und bricht den Lauf nicht ab.

Implementierungs-Status: Das Registry-Feld ``status`` wird NICHT von Hand
gepflegt, sondern hier beim Import automatisch aus der registrierten
Check-Funktion abgeleitet (siehe ``_sync_registry_status``). Ein Check gilt
als implementiert, sobald seine Funktion ``CheckNotImplemented`` wirft —
und als implementiert, sobald ein echter Algorithmus vorliegt. Damit zeigt
das Frontend (GET /api/tests + /api/tests/summary) immer den Code-Stand,
ohne dass beim Anlegen/Implementieren eines Checks ein Status-Feld
nachgezogen werden muss.

Es gibt KEINE Stub-Kategorie mehr: Kriterien sind entweder automatisiert
(implemented) oder manuell (manual). Was nach der Ableitung noch "stub" ist,
wird unten automatisch zum manuellen Kriterium erklärt.
"""
from __future__ import annotations

import importlib
import inspect

from .. import registry as reg
from ._base import CheckContext, CheckNotImplemented, Finding, finding  # noqa: F401

# test_id → check-Funktion (async, erwartet CheckContext)
CHECK_FUNCTIONS: dict[str, callable] = {}

# Registry-Einträge, deren (module, check) sich nicht auflösen ließ
MISSING_CHECKS: list[str] = []


def _build() -> None:
    for entry in reg.REGISTRY:
        test_id = entry["test_id"]
        check_name = entry.get("check")
        module_name = entry.get("module")
        if not check_name or not module_name:
            continue
        try:
            module = importlib.import_module(f"{__name__}.{module_name}")
            fn = getattr(module, check_name)
        except (ImportError, AttributeError) as exc:
            MISSING_CHECKS.append(f"{test_id}: {module_name}.{check_name} ({exc})")
            continue
        CHECK_FUNCTIONS[test_id] = fn


def _ist_stub_check(fn: callable) -> bool:
    """True, wenn die Check-Funktion ein Stub ist (wirft CheckNotImplemented).

    Statische Erkennung über den Funktions-Quelltext: Stub-Module sind
    minimale Platzhalter, deren check_*-Funktion nur ``raise CheckNotImplemented``
    enthält. Sobald ein Algorithmus implementiert wird, verschwindet der
    CheckNotImplemented-Wurf und der Check gilt automatisch als implementiert.
    """
    try:
        source = inspect.getsource(fn)
    except (OSError, TypeError):
        # Nicht inspizierbar (z. B. dynamisch erzeugt) → konservativ als Stub.
        return True
    return "raise CheckNotImplemented" in source


def _sync_registry_status() -> None:
    """Registry-status aus dem tatsächlichen Check-Code ableiten.

    Überschreibt das ``status``-Feld jedes Registry-Eintrags mit dem
    abgeleiteten Wert. Manuelle Kriterien (type="manual") bleiben manuell —
    für sie gibt es keine Check-Funktion.
    """
    for entry in reg.REGISTRY:
        if entry.get("type") == "manual":
            entry["status"] = "manual"
            continue
        fn = CHECK_FUNCTIONS.get(entry["test_id"])
        if fn is not None and not _ist_stub_check(fn):
            entry["status"] = "implemented"
        else:
            entry["status"] = "stub"


_build()
_sync_registry_status()

# Jedes Kriterium ist entweder automatisiert oder manuell. Was nach der
# Auto-Ableitung immer noch "stub" ist (kein implementierter Check und keine
# manuelle Checkliste), wird zum manuellen Kriterium erklärt — der Check ist
# nicht automatisierbar, also bewertet ihn ein Mensch über die manuelle
# Checkliste. type/status="manual", check/module geleert, damit der Check
# weder registriert noch ausgeführt wird (validate_registry: kein
# status=manual mit check-Funktion).
for _entry in reg.REGISTRY:
    if _entry.get("status") == "stub":
        _entry["type"] = "manual"
        _entry["status"] = "manual"
        _entry["check"] = None
        _entry["module"] = None
del _entry


def get_check(test_id: str):
    """Check-Funktion für eine test_id; KeyError, wenn im Registry keine registriert ist."""
    return CHECK_FUNCTIONS[test_id]


__all__ = [
    "CHECK_FUNCTIONS",
    "MISSING_CHECKS",
    "get_check",
    "effective_status",
    "CheckContext",
    "CheckNotImplemented",
    "Finding",
    "finding",
]


def effective_status(test_id: str) -> str:
    """Abgeleiteter Implementierungs-Status für eine test_id (implemented|stub|manual)."""
    entry = reg.get_test(test_id)
    if entry is None:
        return "stub"
    if entry.get("type") == "manual":
        return "manual"
    fn = CHECK_FUNCTIONS.get(test_id)
    if fn is not None and not _ist_stub_check(fn):
        return "implemented"
    return "stub"
