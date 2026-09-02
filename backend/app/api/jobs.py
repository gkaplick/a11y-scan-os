"""
Job-API: Scans anlegen, beobachten, abbrechen/löschen, Ergebnisse + TXT-Export laden.

- POST   /api/jobs                Scan starten (JobCreate)
- GET    /api/jobs                Job-Liste (neueste zuerst)
- GET    /api/jobs/{id}           Einzelner Job
- POST   /api/jobs/{id}/cancel    Scan abbrechen (nur queued/running)
- DELETE /api/jobs/{id}           Scan löschen (nur abgeschlossen; Daten weg)
- GET    /api/jobs/{id}/results   Ergebnisse (by_test / by_url)
- GET    /api/jobs/{id}/export/txt  TXT-Report-Download (+ Datei in docs/)

Der Report wird zusätzlich nach ``settings.output_dir`` (docs/) geschrieben,
damit er als Datei-Ausgabe vorliegt.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from ..config import settings
from ..engine import registry as reg
from ..engine.job_manager import job_manager
from ..engine.screenshots import finding_screenshot_path
from ..schemas import JobCreate, JobOut, ResultsOut, RetestCreate
from ..reports import generate_txt_report
from ..security import require_user

# Router-Dependency: greift vor JEDER Route — auch Screenshot-FileResponse und
# TXT-Export sind damit nur mit gültigem Session-Cookie erreichbar.
router = APIRouter(
    prefix="/api/jobs",
    tags=["jobs"],
    dependencies=[Depends(require_user)],
)


@router.post("", response_model=JobOut, status_code=201)
async def create_job(create: JobCreate) -> JobOut:
    job = await job_manager.create_job(create)
    if job is None:
        raise HTTPException(status_code=500, detail="Job konnte nicht angelegt werden")
    return job


@router.post("/retest", response_model=JobOut, status_code=201)
async def retest_single(create: RetestCreate) -> JobOut:
    """Genau einen Test für genau eine URL erneut ausführen (Mini-Job).

    Aus dem Ergebnis-Frontend: ein einzelner Befund → Retest nur dieses
    Kriteriums auf dieser Seite (inkl. der Auflösung, falls relevant).
    """
    test = reg.get_test(create.test_id)
    if test is None:
        detail = f"Test {create.test_id} nicht im Registry"
        raise HTTPException(status_code=404, detail=detail)
    if test["status"] == "manual":
        raise HTTPException(
            status_code=422,
            detail="Manuelle Kriterien lassen sich nicht automatisiert erneut ausführen",
        )
    job = await job_manager.create_retest(
        str(create.url), create.test_id, test["suite"], create.resolution
    )
    if job is None:
        raise HTTPException(status_code=500, detail="Retest konnte nicht angelegt werden")
    return job


@router.get("", response_model=list[JobOut])
async def list_jobs(limit: int = 50) -> list[JobOut]:
    return await job_manager.list_jobs(limit=min(max(limit, 1), 200))


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str) -> JobOut:
    job = await job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job


@router.post("/{job_id}/cancel", response_model=JobOut)
async def cancel_job(job_id: str) -> JobOut:
    canceled = await job_manager.cancel_job(job_id)
    job = await job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    if not canceled:
        raise HTTPException(status_code=409, detail="Job ist nicht mehr abbrechbar (fertig/fehlgeschlagen)")
    return job


@router.delete("/{job_id}", response_model=JobOut)
async def delete_job(job_id: str) -> JobOut:
    """Löscht einen abgeschlossenen Job samt Seiten/Befunden/Test-Aufzeichnungen."""
    out, status = await job_manager.delete_job(job_id)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    if status == "running":
        raise HTTPException(status_code=409, detail="Laufenden Scan erst abbrechen")
    return out


@router.get("/{job_id}/results", response_model=ResultsOut)
async def get_results(job_id: str) -> ResultsOut:
    results = await job_manager.get_results(job_id)
    if results is None:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return results


@router.get("/{job_id}/screenshots/{finding_id}.png")
async def get_screenshot(job_id: str, finding_id: int) -> FileResponse:
    """Liefert das Element-Screenshot-PNG eines Befunds (bis 400×400).

    Fehlt die Datei (Locator konnte das Element nicht auflösen), antwortet der
    Endpunkt mit 404 — das Frontend blendet das Thumbnail dann aus. Die
    job_id wird gegen das UUID-Format geprüft, damit kein Pfad-Traversal über
    fremde Segmente (z. B. ``..``) möglich ist.
    """
    try:
        uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    path = finding_screenshot_path(job_id, finding_id)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Kein Screenshot für diesen Befund")
    return FileResponse(path, media_type="image/png")


@router.get("/{job_id}/export/txt")
async def export_txt(job_id: str) -> Response:
    """TXT-Report herunterladen (+ Datei in docs/)."""
    job = await job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    results = await job_manager.get_results(job_id)
    if results is None:
        raise HTTPException(status_code=404, detail="Ergebnisse nicht gefunden")

    content = generate_txt_report(results, job).encode("utf-8")
    # Datei zusätzlich nach output_dir schreiben (Reports in docs/)
    filename = _report_filename(job.url, "txt")
    _write_to_output_dir(filename, content)

    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


def _report_filename(url: str, fmt: str) -> str:
    domain = urlparse(url).netloc or url.replace("https://", "").replace("http://", "").split("/")[0]
    domain = domain.replace("www.", "") or "projekt"
    domain = "".join(c if c.isalnum() or c in "-_." else "_" for c in domain)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"Barrierefreiheit_Report_{domain}_{timestamp}.{fmt}"


def _write_to_output_dir(filename: str, content: bytes) -> None:
    os.makedirs(settings.output_dir, exist_ok=True)
    path = os.path.join(settings.output_dir, filename)
    with open(path, "wb") as fh:
        fh.write(content)
