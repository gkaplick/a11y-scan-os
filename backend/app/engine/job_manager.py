"""
Async-Job-Manager: Lebenszyklus der Scans (queued → running → done/failed/canceled).

- Semaphore begrenzt parallele Scans (max_parallel_jobs, Default 3)
- Jeder Job läuft als eigener asyncio.Task (isoliert, abbruchbar)
- Ergebnis-Aggregation über engine/results.py

Die Semaphore hält die gleichzeitige Last begrenzt, ohne dass dafür ein
externer Broker (Redis) nötig ist — die Schnittstelle bleibt aber austauschbar.
"""
from __future__ import annotations

import asyncio
import shutil
import uuid
from datetime import datetime, timezone
from typing import Any

from ..config import settings
from ..db import SessionLocal
from ..models import Job
from ..schemas import JobCreate, JobOut, ResultsOut
from .results import build_results
from .runner import run_job
from .screenshots import job_screenshot_dir


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    """Macht ein Datum zeitzonen-bewusst (SQLite liefert naive UTC-Zeiten).

    Die API gibt damit ISO-Strings mit '+00:00' aus — der Browser parst sie als
    UTC statt fälschlich als lokale Zeit. Sonst zeigt „Läuft seit" immer die
    Zeitzonen-Differenz zuviel an (in Berlin z. B. 2:00:00 statt 0:00:00).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class JobManager:
    def __init__(self, max_parallel: int | None = None) -> None:
        self._semaphore = asyncio.Semaphore(max_parallel or settings.max_parallel_jobs)
        self._tasks: dict[str, asyncio.Task] = {}

    # --- Erzeugen/Starten ---

    async def create_job(self, create: JobCreate) -> JobOut | None:
        job_id = str(uuid.uuid4())
        options: dict[str, Any] = {
            "max_pages": create.max_pages,
            "htaccess_user": create.htaccess_user,
            "htaccess_pw": create.htaccess_pw,
            "resolutions": settings.test_resolutions,
            "disabled_test_ids": list(create.disabled_test_ids),
            "disabled_categories": list(create.disabled_categories),
            "manual_assessments": dict(create.manual_assessments),
        }
        url_str = str(create.url)
        await self._insert_job(job_id, url_str, create.suite, options)
        self._schedule(job_id)
        return await self.get_job(job_id)

    async def create_retest(
        self, url: str, test_id: str, suite: str, resolution: int | None
    ) -> JobOut | None:
        """Anlegen eines Mini-Jobs: genau ein Test, genau eine URL (kein Crawl).

        Der Runner verzweigt über options["retest"] in einen schlanken Pfad.
        """
        job_id = str(uuid.uuid4())
        options: dict[str, Any] = {
            "retest": True,
            "test_ids": [test_id],
            "resolutions": [resolution] if resolution else settings.test_resolutions,
            "htaccess_user": None,
            "htaccess_pw": None,
            "max_pages": 1,
        }
        await self._insert_job(job_id, url, suite, options)
        self._schedule(job_id)
        return await self.get_job(job_id)

    def _schedule(self, job_id: str) -> None:
        task = asyncio.create_task(self._run(job_id), name=f"job-{job_id}")
        self._tasks[job_id] = task

    async def _run(self, job_id: str) -> None:
        async with self._semaphore:
            await run_job(job_id)

    # --- Abbrechen ---

    async def cancel_job(self, job_id: str) -> bool:
        job = await self._get_job(job_id)
        if job is None:
            return False
        task = self._tasks.get(job_id)
        if task is None or task.done():
            return False
        if job.status == "queued":
            # Noch nicht am Semaphore — direkt als canceled markieren
            await self._set_status(job_id, status="canceled", message="Abgebrochen")
            task.cancel()
            return True
        task.cancel()  # Runner setzt status=canceled im CancelledError-Handler
        return True

    # --- Löschen ---

    async def delete_job(self, job_id: str) -> tuple[JobOut | None, str]:
        """Löscht einen abgeschlossenen Job samt Daten (ORM-Cascade).

        Rückgabe (out, status):
        - (JobOut, "deleted")   gelöscht
        - (None, "not_found")   Job existiert nicht
        - (None, "running")     noch queued/running → erst abbrechen
        """
        job = await self._get_job(job_id)
        if job is None:
            return None, "not_found"
        if job.status in ("queued", "running"):
            return None, "running"
        # Task-Registrierung räumen (abgeschlossene Tasks sind hier nicht mehr da)
        self._tasks.pop(job_id, None)
        out = await self.get_job(job_id)  # JobOut vor dem Löschen (Counts)

        def _do() -> None:
            with SessionLocal() as session:
                row = session.get(Job, job_id)
                if row is not None:
                    session.delete(row)  # cascade="all, delete-orphan" räumt
                    session.commit()     # pages/findings/test_records mit ab
            # Element-Screenshots des Jobs ebenfalls entfernen (best-effort)
            shutil.rmtree(job_screenshot_dir(job_id), ignore_errors=True)

        await asyncio.to_thread(_do)
        return out, "deleted"

    # --- Lesen ---

    async def get_job(self, job_id: str) -> JobOut | None:
        row = await self._load_job_with_counts(job_id)
        return self._to_out(row) if row else None

    async def list_jobs(self, limit: int = 50) -> list[JobOut]:
        rows = await self._list_jobs_with_counts(limit)
        return [self._to_out(row) for row in rows]

    async def get_results(self, job_id: str) -> ResultsOut | None:
        return await build_results(job_id)

    # --- Persistenz (sync via to_thread) ---

    async def _insert_job(self, job_id: str, url: str, suite: str, options: dict) -> None:
        def _do() -> None:
            with SessionLocal() as session:
                session.add(
                    Job(
                        id=job_id,
                        url=url,
                        suite=suite,
                        options=options,
                        status="queued",
                        created_at=utcnow(),
                    )
                )
                session.commit()

        await asyncio.to_thread(_do)

    async def _set_status(self, job_id: str, **fields: Any) -> None:
        def _do() -> None:
            with SessionLocal() as session:
                job = session.get(Job, job_id)
                if job is None:
                    return
                for key, value in fields.items():
                    setattr(job, key, value)
                session.commit()

        await asyncio.to_thread(_do)

    async def _get_job(self, job_id: str) -> Job | None:
        def _do() -> Job | None:
            with SessionLocal() as session:
                return session.get(Job, job_id)

        return await asyncio.to_thread(_do)

    async def _load_job_with_counts(self, job_id: str):
        def _do():
            with SessionLocal() as session:
                job = session.get(Job, job_id)
                if job is None:
                    return None
                from ..models import Finding, Page

                page_count = session.query(Page).filter(Page.job_id == job_id).count()
                finding_count = session.query(Finding).filter(Finding.job_id == job_id).count()
                return job, page_count, finding_count

        return await asyncio.to_thread(_do)

    async def _list_jobs_with_counts(self, limit: int):
        def _do():
            with SessionLocal() as session:
                from ..models import Finding, Page

                jobs = (
                    session.query(Job).order_by(Job.created_at.desc()).limit(limit).all()
                )
                result = []
                for job in jobs:
                    page_count = session.query(Page).filter(Page.job_id == job.id).count()
                    finding_count = session.query(Finding).filter(Finding.job_id == job.id).count()
                    result.append((job, page_count, finding_count))
                return result

        return await asyncio.to_thread(_do)

    def _to_out(self, row) -> JobOut:
        job, page_count, finding_count = row
        return JobOut(
            id=job.id,
            url=job.url,
            suite=job.suite,
            status=job.status,
            progress=job.progress,
            current_url=job.current_url,
            message=job.message,
            error=job.error,
            created_at=as_utc(job.created_at),
            started_at=as_utc(job.started_at),
            finished_at=as_utc(job.finished_at),
            page_count=page_count,
            finding_count=finding_count,
        )


# Singleton — wird in api/jobs.py genutzt
job_manager = JobManager()
