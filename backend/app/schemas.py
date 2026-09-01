"""
Pydantic-Schemas der REST-/WebSocket-API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

SuiteName = Literal["bitv", "wcag", "all"]
JobStatus = Literal["queued", "running", "done", "failed", "canceled"]


class JobCreate(BaseModel):
    url: HttpUrl
    suite: SuiteName = "bitv"
    max_pages: int | None = Field(default=1, ge=1)  # Default 1 Seite (0/null = unbegrenzt)
    htaccess_user: str | None = None
    htaccess_pw: str | None = None
    # Vom Nutzer als "nicht relevant" deaktivierte Tests: werden im Scan nicht
    # ausgeführt und im Ergebnis als Status "nicht_relevant" geführt (kein
    # Einfluss auf die Gesamtauswertung).
    disabled_test_ids: list[str] = Field(default_factory=list)
    disabled_categories: list[str] = Field(default_factory=list)
    # Manuelle Bewertungen für nicht automatisierbare Kriterien (z. B. die
    # BITV-Abschnitte 6/7/11/12): test_id → "erfuellt" | "nicht_erfuellt" |
    # "nicht_anwendbar". Betroffene Tests werden im Scan nicht ausgeführt,
    # im Ergebnis-Snapshot als Status "manual" geführt und fließen in die
    # System-Bewertung ein (nicht_anwendbar/erfuellt = bestanden).
    manual_assessments: dict[str, str] = Field(default_factory=dict)
    # Host-Einschränkung: nur eine URL pro Job (Mehrfach-Projekte später)


class RetestCreate(BaseModel):
    """Einzelnen Test für eine einzelne URL erneut ausführen (aus dem Ergebnis)."""
    url: HttpUrl
    test_id: str
    resolution: int | None = None


class JobOut(BaseModel):
    id: str
    url: str
    suite: str
    status: JobStatus
    progress: float
    current_url: str | None = None
    message: str | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    page_count: int = 0
    finding_count: int = 0


class ProgressEvent(BaseModel):
    type: Literal["page", "stage", "status", "done", "error", "log"] = "log"
    job_id: str
    percent: float
    page_url: str | None = None
    page_index: int | None = None
    page_total: int | None = None
    resolution: int | None = None
    message: str
    at: datetime


class FindingOut(BaseModel):
    id: int                       # DB-ID — Basis für die Screenshot-URL
    screenshot: bool = False      # Screenshot-Datei vorhanden → Thumbnail anzeigen
    test_id: str
    url: str
    dom_path: str
    message: str
    detail: str | None = None
    resolution: int | None = None
    number: str | None = None       # einzige Norm-Nummer (entry["id"])
    category: str | None = None     # WCAG | EN 301 549 | BITV
    level: str
    wcag_level: str | None = None
    responsibility: str
    priority: str


class TestOut(BaseModel):
    id: str                       # einzige Norm-Nr. des Tests (z. B. "1.1.1", "7.2.1", "9.1.4.3")
    test_id: str                  # maschinenlesbare ID (z. B. "WCAG_1_1_1_IMG_ALT")
    title: str
    suite: str
    level: str
    wcag_level: str | None = None
    category: str
    responsibility: str
    priority: str
    type: str
    status: str                   # implemented|manual|nicht_relevant (keine Stubs mehr)
    description: str
    solution: str
    test_hint: str
    # Manuelle Bewertung dieses Tests aus dem Scan (test_id → "erfuellt" |
    # "nicht_erfuellt" | "nicht_anwendbar"); None wenn nicht manuell bewertet.
    assessment: str | None = None
    # EN 301 549: zugrunde liegende BITV/WCAG-Test-IDs (Ergebnis wird geerbt).
    en_sources: list[str] = Field(default_factory=list)
    # Ergebnis dieses Tests in der System-Bewertung (aus der Aggregation):
    # bestanden | nicht_bestanden | nicht_anwendbar | nicht_bewertet.
    # Für EN-Tests das geerbte Ergebnis (aus den Quell-Tests).
    result: str = "nicht_bewertet"
    # EN 301 549: Einordnung des Kriteriums — "verbindlich" (WCAG A/AA bzw.
    # EN-Kapitel 5–12) | "erweitert" (WCAG-AAA, informatorisch aufgeführt).
    # None für BITV-Kriterien (kein EN-Kriterium).
    en_kind: str | None = None


class ResultByTest(BaseModel):
    """Perspektive 1: je Test die gefundenen URLs (POV der Fehlerart)."""
    test_id: str
    title: str
    suite: str
    level: str
    wcag_level: str | None = None   # nur WCAG-System: A/AA/AAA (sonst None)
    number: str | None = None
    category: str | None = None
    responsibility: str
    priority: str
    count: int
    urls: list[str]
    findings: list[FindingOut]


class ResultByUrl(BaseModel):
    """Perspektive 2: je URL die gefundenen Fehler."""
    url: str
    http_status: int | None = None
    ok: bool
    error: str | None = None
    finding_count: int
    findings: list[FindingOut]


class LevelZaehlung(BaseModel):
    """WCAG-Level-Aufschlüsselung (nur für das System „WCAG")."""
    level: str            # "A" | "AA" | "AAA"
    gesamt: int           # implementierte Tests dieses Levels
    bestanden: int
    nicht_bestanden: int


class SystemBewertungOut(BaseModel):
    """Gesamturteil je Testsystem (BITV / WCAG / EN 301 549), pro Projekt.

    BITV/EN sind binär (bestanden/nicht bestanden), WCAG ist abgestuft über
    das erzielte Konformitätsniveau (A/AA/AAA). Nur implementierte Checks
    werden bewertet; manuelle Kriterien (Status manual) zählen als „nicht
    automatisiert".
    """
    system: str                    # "BITV" | "WCAG" | "EN 301 549"
    urteil: str                    # "bestanden" | "nicht bestanden" | "nicht bewertbar"
    gesamt: int                    # implementierte (bewertbare) Tests
    bestanden: int                 # keine Befunde (BITV: NA-Default zählt als bestanden)
    nicht_bestanden: int           # ≥1 Befund projektweit
    nicht_automatisiert: int       # Status manual
    niveau: str | None = None      # nur WCAG: "A" | "AA" | "AAA" | "kein Level erfüllt"
    level_verteilung: list[LevelZaehlung] = []   # nur WCAG
    # Nur EN 301 549: Anzahl der erweiterten (WCAG-AAA) Kriterien, die bewertet
    # wurden. Diese sind informatorisch — sie zählen nicht ins EN-Urteil
    # (verbindlich sind A/AA und die EN-Kapitel 5–12).
    erweitert: int = 0


class ResultsOut(BaseModel):
    job_id: str
    suite: str
    status: str
    by_test: list[ResultByTest]
    by_url: list[ResultByUrl]
    page_count: int
    total_findings: int
    tests: list[TestOut]        # Registry-Stand des Laufs
    manual_tests: list[TestOut]  # nicht automatisierbare Kriterien (Checkliste)
    system_bewertung: list[SystemBewertungOut] = []   # je Testsystem ein Urteil
