"""
Job-Manager-Lifecycle-Tests (mit Fake-Runner — kein echtes Crawling/Playwright).

Getestet wird der Zustandsübergang queued → running → done bzw. → canceled
sowie das Semaphore-Verhalten (parallele Scans begrenzt). Der echte Runner
wird über monkeypatch durch eine kontrollierbare Fake-Funktion ersetzt.
"""
from __future__ import annotations

import asyncio

import app.engine.job_manager as jm_module
from app.db import SessionLocal
from app.engine.job_manager import JobManager
from app.models import Job
from app.schemas import JobCreate


def _update_job(job_id: str, **fields):
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None:
            return
        for key, value in fields.items():
            setattr(job, key, value)
        session.commit()


async def _poll(manager: JobManager, job_id: str, wanted: str, tries: int = 200) -> str:
    for _ in range(tries):
        out = await manager.get_job(job_id)
        if out.status == wanted:
            return out.status
        await asyncio.sleep(0.01)
    raise AssertionError(f"Job {job_id} wurde nicht {wanted} (zuletzt {out.status})")


def _create(url: str) -> JobCreate:
    return JobCreate(url=url, suite="bitv", max_pages=1)


# --------------------------------------------------- "Nicht relevante" Tests

def test_partition_tests():
    """Deaktivierte Tests (per test_id oder Kategorie) fliegen aus 'active',
    bleiben aber mit Status 'nicht_relevant' im Snapshot."""
    from app.engine.runner import partition_tests
    from app.engine import registry as reg

    selected = reg.get_tests_for_suite("all")
    disabled_id = next(t["test_id"] for t in selected if t["category"] == "BITV")
    active, snapshot = partition_tests(selected, {disabled_id}, {"EN 301 549"})

    assert len(active) < len(selected)
    assert all(t["test_id"] != disabled_id for t in active)
    assert all(t["category"] != "EN 301 549" for t in active)

    # Snapshot: aktiv unverändert, deaktiviert markiert, Reihenfolge = Registry
    assert [t["test_id"] for t in snapshot] == [t["test_id"] for t in selected]
    for t in snapshot:
        assert t["test_id"] == disabled_id or t["category"] == "EN 301 549" or t["status"] != "nicht_relevant"
    nr = [t for t in snapshot if t["status"] == "nicht_relevant"]
    assert {t["test_id"] for t in nr} == {disabled_id} | {
        t["test_id"] for t in selected if t["category"] == "EN 301 549"
    }


async def test_create_job_stores_disabled_tests(monkeypatch):
    """disabled_test_ids/-categories landen im Job-Options (werden vom Runner gelesen)."""
    async def fake_run(job_id):
        pass

    monkeypatch.setattr(jm_module, "run_job", fake_run)
    manager = JobManager(max_parallel=2)
    create = JobCreate(
        url="https://example.com/",
        suite="bitv",
        max_pages=1,
        disabled_test_ids=["BITV_9_1_2_1_ALTERNATIVEN_FUER_AUDIODATEIEN_UND_STUMME_VIDEOS"],
        disabled_categories=["EN 301 549"],
    )
    out = await manager.create_job(create)
    assert out is not None
    with SessionLocal() as session:
        row = session.get(Job, out.id)
        assert row is not None
        assert row.options["disabled_test_ids"] == [
            "BITV_9_1_2_1_ALTERNATIVEN_FUER_AUDIODATEIEN_UND_STUMME_VIDEOS"
        ]
        assert row.options["disabled_categories"] == ["EN 301 549"]


# ------------------------------------------------------------------ Lifecycle

async def test_create_job_persists_queued(monkeypatch):
    """K3: run_job muss gefakt sein — sonst startet ein echter Browser-Scan."""
    async def fake_run(job_id):
        pass  # kein echtes Crawling/Playwright in Unit-Tests

    monkeypatch.setattr(jm_module, "run_job", fake_run)
    manager = JobManager(max_parallel=2)
    out = await manager.create_job(_create("https://example.com/"))
    assert out is not None
    assert out.status in {"queued", "running"}
    assert out.url == "https://example.com/"
    assert out.suite == "bitv"
    # Job ist persistiert
    cur = await manager.get_job(out.id)
    assert cur is not None


async def test_lifecycle_queued_to_done(monkeypatch):
    calls = []

    async def fake_run(job_id):
        calls.append(job_id)
        await asyncio.to_thread(_update_job, job_id, status="done", progress=100.0)

    monkeypatch.setattr(jm_module, "run_job", fake_run)
    manager = JobManager(max_parallel=1)
    out = await manager.create_job(_create("https://example.com/"))
    status = await _poll(manager, out.id, "done")
    assert status == "done"
    assert calls == [out.id]
    final = await manager.get_job(out.id)
    assert final.progress == 100.0


async def test_get_missing_job_returns_none():
    manager = JobManager(max_parallel=1)
    assert await manager.get_job("gibt-es-nicht") is None
    assert await manager.get_results("gibt-es-nicht") is None


# --------------------------------------------------------------------- Cancel

async def test_cancel_queued_behind_semaphore(monkeypatch):
    """Job 2 hängt hinter Job 1 am Semaphore → direkt als canceled markierbar."""
    started1 = asyncio.Event()
    release1 = asyncio.Event()

    async def fake_run(job_id):
        started1.set()
        await release1.wait()

    monkeypatch.setattr(jm_module, "run_job", fake_run)
    manager = JobManager(max_parallel=1)

    await manager.create_job(_create("https://one.example/"))
    await asyncio.wait_for(started1.wait(), timeout=5)  # Job 1 hält das Semaphore
    out2 = await manager.create_job(_create("https://two.example/"))

    assert await manager.cancel_job(out2.id) is True
    canceled = await manager.get_job(out2.id)
    assert canceled.status == "canceled"

    # Aufräumen: Job 1 normal beenden
    release1.set()
    await asyncio.sleep(0.05)


async def test_cancel_running(monkeypatch):
    """Läuft der Runner, wird die Task gecancelt; der Runner-Handler markiert canceled."""
    block = asyncio.Event()

    async def fake_run(job_id):
        await asyncio.to_thread(_update_job, job_id, status="running")
        try:
            await block.wait()
        except asyncio.CancelledError:
            await asyncio.to_thread(_update_job, job_id, status="canceled", message="Abgebrochen")
            raise

    monkeypatch.setattr(jm_module, "run_job", fake_run)
    manager = JobManager(max_parallel=1)
    out = await manager.create_job(_create("https://cancel.example/"))

    for _ in range(200):
        cur = await manager.get_job(out.id)
        if cur.status == "running":
            break
        await asyncio.sleep(0.01)
    assert cur.status == "running"

    assert await manager.cancel_job(out.id) is True
    status = await _poll(manager, out.id, "canceled")
    assert status == "canceled"


async def test_cancel_done_job_returns_false(monkeypatch):
    async def fake_run(job_id):
        await asyncio.to_thread(_update_job, job_id, status="done")

    monkeypatch.setattr(jm_module, "run_job", fake_run)
    manager = JobManager(max_parallel=1)
    out = await manager.create_job(_create("https://example.com/"))
    await _poll(manager, out.id, "done")
    assert await manager.cancel_job(out.id) is False


# ------------------------------------------------------------ Parallelität

async def test_semaphore_limits_parallel_runs(monkeypatch):
    """Bei max_parallel=1 startet Job 2 erst, wenn Job 1 fertig ist."""
    running = 0
    max_running = 0
    started = asyncio.Event()

    async def fake_run(job_id):
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        started.set()
        await asyncio.sleep(0.05)
        running -= 1
        await asyncio.to_thread(_update_job, job_id, status="done")

    monkeypatch.setattr(jm_module, "run_job", fake_run)
    manager = JobManager(max_parallel=1)

    out1 = await manager.create_job(_create("https://one.example/"))
    await started.wait()
    out2 = await manager.create_job(_create("https://two.example/"))

    await _poll(manager, out1.id, "done")
    await _poll(manager, out2.id, "done")

    assert max_running <= 1
    assert running == 0
