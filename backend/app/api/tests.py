"""
Test-Registry-API.

``GET /api/tests`` liefert den kompletten Katalog (automatisierte + manuell
zu prüfende Kriterien) — Basis für die Abdeckungs-Map im Frontend, die sich
damit automatisch am Registry-Stand des Scripts aktualisiert.
"""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, HTTPException

from ..engine import registry as reg
from ..schemas import TestOut

router = APIRouter(prefix="/api/tests", tags=["tests"])


def _to_out(entry: dict) -> TestOut:
    return TestOut(
        id=entry["id"],
        test_id=entry["test_id"],
        title=entry["title"],
        suite=entry["suite"],
        level=entry["level"],
        wcag_level=entry.get("wcag_level") or None,
        category=entry["category"],
        responsibility=entry["responsibility"],
        priority=entry["priority"],
        type=entry["type"],
        status=entry["status"],
        description=entry.get("description", ""),
        solution=entry.get("solution", ""),
        test_hint=entry.get("test_hint", ""),
        en_sources=reg.get_en_source_test_ids(entry["test_id"]),
    )


@router.get("/summary")
async def registry_summary() -> dict:
    """Aggregierte Kennzahlen für die Abdeckungs-Map (automatisch aus Registry)."""
    entries = reg.REGISTRY
    by_status = Counter(e["status"] for e in entries)
    by_suite = Counter(e["suite"] for e in entries)
    by_category = Counter(e["category"] for e in entries)
    by_level = Counter(e["level"] for e in entries)
    return {
        "total": len(entries),
        "by_status": dict(by_status),
        "by_suite": dict(by_suite),
        "by_category": dict(by_category),
        "by_level": dict(by_level),
    }


@router.get("", response_model=list[TestOut])
async def list_tests(suite: str | None = None, status: str | None = None) -> list[TestOut]:
    """Registry auflisten; optional gefiltert nach Suite und Status."""
    entries = reg.get_tests_for_suite(suite) if suite else list(reg.REGISTRY)
    if status:
        entries = [e for e in entries if e["status"] == status]
    return [_to_out(e) for e in entries]


@router.get("/{test_id}", response_model=TestOut)
async def get_test(test_id: str) -> TestOut:
    entry = reg.get_test(test_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Test nicht gefunden")
    return _to_out(entry)
