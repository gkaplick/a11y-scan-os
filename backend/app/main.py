"""
FastAPI-App des a11y-Scanners.

Lifespan: DB-Schema anlegen, Playwright-Browser warmstarten (best-effort,
wird bei Bedarf pro Job ohnehin gestartet), beim Shutdown schließen.

Routen:
- /api/auth     Login/Logout/me + WS-Ticket (kein Registrierungsweg)
- /api/jobs      Scans (anlegen/listen/abbrechen/Ergebnisse/Export)
- /api/tests     Test-Registry (inkl. Summary für die Abdeckungs-Map)
- /ws/jobs/{id}  Live-Progress
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, jobs, tests, ws
from .config import settings
from .db import init_db
from .engine.browser import close_browser, get_browser
from .security import ensure_admin


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    # Beim allerersten Start den Admin aus A11Y_ADMIN_USERNAME/-PASSWORD anlegen
    # (nur, wenn users leer ist). Weitere Zugänge: `python -m app.manage …`.
    await ensure_admin()
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

# Login-Pflicht seit der Auth-Einführung: CORS nur für explizit erlaubte
# Origins (keine Wildcard). Das SPA läuft same-origin über den Nitro-Proxy —
# Cross-Origin-Zugriffe sind nicht vorgesehen, Cookies werden nur so gesetzt.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
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
