"""
FastAPI-App des a11y-Scanners.

Lifespan: DB-Schema anlegen, Playwright-Browser warmstarten (best-effort,
wird bei Bedarf pro Job ohnehin gestartet), beim Shutdown schließen.

Routen:
- /api/jobs      Scans (anlegen/listen/abbrechen/Ergebnisse/Export)
- /api/tests     Test-Registry (inkl. Summary für die Abdeckungs-Map)
- /ws/jobs/{id}  Live-Progress
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import jobs, tests, ws
from .config import settings
from .db import init_db
from .engine.browser import close_browser, get_browser


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    # Browser warmstarten (nur, wenn konfiguriert) — falls Chromium noch nicht
    # bereit ist (erster Start lädt die Binaries), wird das hier verschluckt;
    # der erste Job startet ihn ohnehin über new_context() → get_browser().
    # Im Dev-Modus (A11Y_BROWSER_WARMSTART=false) kein Warmstart: ein offener
    # Browser hielte sonst den uvicorn-Reload-Shutdown auf (→ API hängt).
    if settings.browser_warmstart:
        try:
            await get_browser()
        except Exception:
            pass
    yield
    try:
        await close_browser()
    except Exception:
        pass


app = FastAPI(
    title="A11Y Scanner API",
    description="Barrierefreiheits-Scanner (BITV 2.0 / WCAG 2.1 / EN 301 549)",
    version="1.0.0",
    lifespan=lifespan,
)

# Lokales Single-User-Tool ohne Auth — CORS großzügig (Nuxt-Dev-/Prod-Origin
# wird i. d. R. ohnehin über den Nitro-Proxy gefahren → same-origin).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(tests.router)
app.include_router(ws.router)


@app.get("/")
async def root() -> dict:
    return {
        "service": "a11y-scanner",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": ["/api/jobs", "/api/tests", "/ws/jobs/{job_id}"],
    }


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
