"""
Scan-Runner: führt einen Job aus — Crawl + pro Seite Check-Dispatch + Persistenz
+ Progress-Events an den ProgressBroker.

Ablauf pro Seite:
1. HEAD-Pre-Check (überspringen bei Nicht-HTML / HTTP-Fehler, 404 wird notiert)
2. page.goto (domcontentloaded) + best-effort networkidle
3. Syntax-Checks (1×, ctx.soup) und Resolution-Checks (pro Auflösung, ctx.page)
4. Findings persistieren (denormalisierte Registry-Metadaten)
5. Links sammeln → interne URLs in die Crawler-Queue (max_pages respektieren)

Stub-Checks (CheckNotImplemented) werden geschluckt und über den TestRecord-
Snapshot als "noch nicht implementiert" geführt. Manuelle Kriterien (type=manual)
laufen gar nicht — sie erscheinen im Ergebnis als Checkliste.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from bs4 import BeautifulSoup

from ..config import settings
from ..db import SessionLocal
from ..models import Finding, Job, Page, TestRecord
from ..schemas import ProgressEvent
from . import registry as reg
from .browser import new_context
from .checks import CheckContext, CheckNotImplemented, get_check
from .crawler import Crawler
from .progress import broker
from .screenshots import capture_findings_screenshots

logger = logging.getLogger(__name__)

# Tastatur-/Fokus-Checks laufen nur auf Desktop-Breiten (> keyboard_min_width).
# Das Gate liest das Registry-Feld ``desktop_only`` (statt eines Modul-Sets).

# W3C-Tests, die nur für die ersten N Seiten laufen (w3c_validator_max)
_W3C_TEST_IDS = {"WCAG_4_1_1_HTML_ERROR", "WCAG_4_1_1_HTML_WARNING"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def partition_tests(
    selected: list[dict],
    disabled_ids: set[str],
    disabled_cats: set[str],
    assessments: dict[str, str] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Trennt die Suite in aktive Tests und Snapshot-Einträge.

    Vom Nutzer deaktivierte Tests (per test_id oder ganze Kategorie) werden
    nicht ausgeführt, bleiben aber im Ergebnis-Snapshot mit
    status="nicht_relevant" sichtbar (kein Einfluss auf die Bewertung).

    Manuell bewertete Tests (assessments: test_id → "erfuellt" | "nicht_erfuellt"
    | "nicht_anwendbar") werden nicht ausgeführt und im Snapshot als
    status="manual" geführt — ihre Bewertung fließt über die System-Bewertung
    in results.py ein. WICHTIG: Deaktiviert (disabled) schlägt manuell — ein
    als "nicht relevant" deaktivierter Test ist NICHT Teil des Endberichts,
    seine Dropdown-Bewertung greift erst, wenn der Nutzer ihn aktiviert.

    Rückgabe: (aktive Tests zum Ausführen, Snapshot-Liste für _snapshot_tests).
    """
    assessments = assessments or {}
    manual_ids = set(assessments)

    def _is_disabled(t: dict) -> bool:
        return t["test_id"] in disabled_ids or t["category"] in disabled_cats

    active = [t for t in selected if not _is_disabled(t) and t["test_id"] not in manual_ids]
    snapshot = []
    for t in selected:
        if _is_disabled(t):
            snapshot.append({**t, "status": "nicht_relevant"})
        elif t["test_id"] in manual_ids:
            snapshot.append({**t, "status": "manual"})
        else:
            snapshot.append(t)
    return active, snapshot


# --- Persistenz (sync Session via to_thread) ---

async def _update_job(job_id: str, **fields: Any) -> None:
    def _do() -> None:
        with SessionLocal() as session:
            job = session.get(Job, job_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)
            session.commit()

    await asyncio.to_thread(_do)


async def _snapshot_tests(job_id: str, tests: list[dict]) -> None:
    def _do() -> None:
        with SessionLocal() as session:
            for t in tests:
                session.add(
                    TestRecord(
                        job_id=job_id,
                        test_id=t["test_id"],
                        title=t["title"],
                        suite=t["suite"],
                        level=t["level"],
                        wcag_level=t.get("wcag_level") or None,
                        category=t["category"],
                        number=t.get("id") or None,
                        responsibility=t["responsibility"],
                        priority=t["priority"],
                        type=t["type"],
                        status=t["status"],
                    )
                )
            session.commit()

    await asyncio.to_thread(_do)


async def _insert_page(job_id: str, url: str, http_status: int | None, ok: bool, error: str | None) -> None:
    def _do() -> None:
        with SessionLocal() as session:
            session.add(
                Page(
                    job_id=job_id,
                    url=url,
                    http_status=http_status,
                    ok=ok,
                    error=error,
                    visited_at=utcnow(),
                )
            )
            session.commit()

    await asyncio.to_thread(_do)


async def _insert_findings(job_id: str, rows: list[dict]) -> list[int]:
    """Persistiert Befunde und liefert die DB-IDs (für Screenshot-Dateinamen).

    Die IDs sind mit ``rows`` gleichsinnig sortiert — der Runner benennt die
    Element-Screenshots nach den Finding-IDs (``{id}.png``).
    """
    if not rows:
        return []

    def _do() -> list[int]:
        with SessionLocal() as session:
            objs = [Finding(job_id=job_id, **row) for row in rows]
            session.add_all(objs)
            session.flush()  # Auto-Increment-IDs zuweisen
            ids = [o.id for o in objs]
            session.commit()
            return ids

    return await asyncio.to_thread(_do)


async def _insert_broken_links(job_id: str, crawler: Crawler) -> None:
    """Persistiert tote Links als Findings (Pseudo-Test LINKS_404).

    url = Fundseite, dom_path = Ziel-Link. Ohne Registry-Metadaten (kein
    normatives Kriterium) — die Reports zeigen sie als eigene Rubrik.
    """
    rows: list[dict] = []
    for page_url, links in crawler.broken_links.items():
        for broken in sorted(set(links)):
            rows.append(
                {
                    "test_id": "LINKS_404",
                    "url": page_url,
                    "dom_path": broken,
                    "message": "Toter Link (404)",
                    "detail": f"Linkziel: {broken}",
                    "resolution": None,
                    "number": "",
                    "category": "",
                    "level": "MUSS",
                    "wcag_level": "",
                    "responsibility": "technisch",
                    "priority": "mittel",
                }
            )
    if rows:
        await _insert_findings(job_id, rows)


# --- Progress ---

async def _emit(
    job_id: str,
    event_type: str,
    message: str,
    *,
    percent: float | None = None,
    page_url: str | None = None,
    page_index: int | None = None,
    page_total: int | None = None,
    resolution: int | None = None,
) -> None:
    event = ProgressEvent(
        type=event_type,
        job_id=job_id,
        percent=percent if percent is not None else 0.0,
        page_url=page_url,
        page_index=page_index,
        page_total=page_total,
        resolution=resolution,
        message=message,
        at=utcnow(),
    )
    await broker.publish(event)


# --- Seiten-Load ---

async def _load_page(page, url: str) -> dict:
    """Lädt eine URL und liefert soup/status/html. Bei Fehlern: {'error': ...}.

    Einmaliger Retry mit kurzem Backoff: transiente Timeouts (z. B. wenn
    parallel ein zweiter Scan denselben Playwright-Browser nutzt oder die
    Website kurz zögert) sollen einen Scan nicht sofort scheitern lassen.
    """
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            response = await page.goto(
                url,
                timeout=settings.request_timeout * 1000,
                wait_until="domcontentloaded",
            )
            break
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt == 1:
                await asyncio.sleep(1.5)
    else:
        return {"error": str(last_error)}

    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass  # networkidle ist best-effort

    try:
        html = await page.content()
        status = response.status if response is not None else 0
        soup = BeautifulSoup(html, "html.parser")
        return {"status": status, "html": html, "soup": soup}
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        return {"error": str(exc)}


# --- Hauptlauf ---

async def run_job(job_id: str) -> None:
    """Führt den Job vollständig aus (Crawl + Checks). Aufruf als asyncio.Task."""
    job = await asyncio.to_thread(_get_job, job_id)
    if job is None:
        return

    options = job.options or {}
    suite = job.suite or "bitv"
    max_pages = options.get("max_pages") or settings.max_pages_per_project or None
    htaccess_user = options.get("htaccess_user") or settings.htaccess_user or None
    htaccess_pw = options.get("htaccess_pw") or settings.htaccess_pw or None
    resolutions = list(options.get("resolutions") or settings.test_resolutions)
    if not resolutions:
        resolutions = [320, 1920]

    # Retest-Flow (ein Test, eine URL): kein Crawl — nur der ausgewählte Check
    if options.get("retest"):
        retest_ids = options.get("test_ids") or []
        retest_tests = [t for t in reg.REGISTRY if t["test_id"] in retest_ids]
        if retest_tests:
            await _run_retest(job_id, job, retest_tests, resolutions, htaccess_user, htaccess_pw)
            return
        # K4: lösen sich die Retest-test_ids in keine Registry-Tests auf, ist das
        # ein Nutzerfehler — Job als failed markieren statt still Voll-Scan zu starten.
        msg = f"Retest fehlgeschlagen: unbekannte test_ids: {', '.join(retest_ids) or '(leer)'}"
        await _update_job(job_id, status="failed", error=msg, finished_at=utcnow(), message=msg)
        await _emit(job_id, "error", msg)
        return

    # Test-Auswahl laut Suite. Als "nicht relevant" deaktivierte Tests werden
    # weder ausgeführt noch bewertet — sie erscheinen im Ergebnis nur als
    # Snapshot mit Status "nicht_relevant" (sichtbar, aber ausgegraut).
    selected = reg.get_tests_for_suite(suite)
    active, snapshot = partition_tests(
        selected,
        set(options.get("disabled_test_ids") or []),
        set(options.get("disabled_categories") or []),
        options.get("manual_assessments") or {},
    )
    syntax_tests = [t for t in active if t["type"] == "syntax"]
    resolution_tests = [t for t in active if t["type"] == "resolution"]

    # Seitenübergreifender Zustand für Konsistenz-Checks (Navigation/Bezeichnung):
    # alle Syntax-Checks des Jobs teilen sich das Dict, damit sie Signaturen
    # über mehrere Seiten hinweg vergleichen können.
    job_state: dict = {}

    await _snapshot_tests(job_id, snapshot)
    await _update_job(job_id, status="running", started_at=utcnow(), progress=0.0)
    disabled_n = len(snapshot) - len(active)
    suffix = f" ({disabled_n} Tests als nicht relevant deaktiviert)" if disabled_n else ""
    await _emit(job_id, "status", f"Scan gestartet: {suite}-Suite für {job.url}{suffix}")

    context = None
    pages_done = 0
    ok_pages = 0  # erfolgreich geprüfte Seiten (Ladefehler/404 zählen nicht)
    try:
        context, page = await new_context(htaccess_user, htaccess_pw)
        crawler = Crawler(job.url, max_pages=max_pages, htaccess_user=htaccess_user, htaccess_pw=htaccess_pw)

        while crawler.has_more():
            if max_pages is not None and pages_done >= max_pages:
                break

            url = crawler.next_url()
            if url is None:
                break
            crawler.mark_visited(url)
            is_first_page = pages_done == 0

            await _update_job(job_id, current_url=url, message=f"Prüfe {url}")
            await _emit(
                job_id, "page", f"Prüfe Seite: {url}",
                page_url=url, page_index=pages_done + 1, page_total=max_pages,
            )

            # 1) HEAD-Pre-Check (best-effort; Netzwerkfehler ⇒ fallback auf goto)
            try:
                status, ctype = await crawler.head_info(url)
                if status != 200:
                    if status == 404:
                        crawler.note_404(url, url)
                        await _insert_page(job_id, url, 404, False, "Seite nicht gefunden (404)")
                    else:
                        await _insert_page(job_id, url, status, False, f"HTTP {status}")
                    await _emit(job_id, "log", f"Seite übersprungen: HTTP {status}")
                    pages_done += 1
                    continue
                if ctype and not ctype.lower().startswith("text/html"):
                    await _insert_page(job_id, url, status, True, None)
                    await _emit(job_id, "log", f"Kein HTML ({ctype.split(';')[0]}), übersprungen")
                    pages_done += 1
                    continue
            except Exception:
                pass  # HEAD fehlgeschlagen → trotzdem mit Playwright versuchen

            # 2) Seite laden
            loaded = await _load_page(page, url)
            if "error" in loaded:
                await _insert_page(job_id, url, None, False, loaded["error"])
                await _emit(job_id, "log", f"Fehler beim Laden: {loaded['error']}")
                pages_done += 1
                continue

            soup = loaded["soup"]
            http_status = loaded.get("status", 0)

            # Nicht-200-Seiten: keine Checks, 404 wird notiert
            if http_status and http_status != 200:
                if http_status == 404:
                    crawler.note_404(url, url)
                await _insert_page(job_id, url, http_status, ok=(http_status < 400), error=None)
                await _emit(job_id, "log", f"Seite übersprungen: HTTP {http_status}")
                pages_done += 1
                continue

            await _insert_page(job_id, url, http_status, True, None)

            # 3) Checks
            findings_rows: list[dict] = []

            # W3C-Aktivstatus pro Seite aktualisieren
            w3c_active = (
                settings.w3c_validator_max != 0
                and (settings.w3c_validator_max == -1 or pages_done < settings.w3c_validator_max)
            )

            for test in syntax_tests:
                test_id = test["test_id"]
                if test_id in _W3C_TEST_IDS and not w3c_active:
                    continue
                ctx = _make_ctx(url, soup, page, None, test_id, htaccess_user, htaccess_pw, w3c_active, is_first_page, job_state)
                rows = await _run_check(ctx, test, url)
                findings_rows.extend(rows)

            for resolution in resolutions:
                await page.set_viewport_size({"width": resolution, "height": 1080})
                await page.wait_for_timeout(150)
                for test in resolution_tests:
                    test_id = test["test_id"]
                    if test.get("desktop_only") and resolution <= settings.keyboard_min_width:
                        continue
                    ctx = _make_ctx(url, soup, page, resolution, test_id, htaccess_user, htaccess_pw, w3c_active, is_first_page, job_state)
                    rows = await _run_check(ctx, test, url)
                    findings_rows.extend(rows)
            # Viewport zurücksetzen (Default = erste Auflösung)
            await page.set_viewport_size({"width": resolutions[0], "height": 1080})

            # K2: Resolution-Checks, die Findings ohne resolution-Feld liefern
            # (z. B. text_spacing), melden dieselbe Stelle bei 320 und 1920
            # identisch — pro Seite bleibt jede Meldung einmal.
            deduped: list[dict] = []
            seen: set[tuple] = set()
            for row in findings_rows:
                if row["resolution"] is None:
                    key = (row["test_id"], row["url"], row["dom_path"], row["message"])
                    if key in seen:
                        continue
                    seen.add(key)
                deduped.append(row)
            findings_rows = deduped

            # 4) Persistieren
            finding_ids = await _insert_findings(job_id, findings_rows)
            found = len(findings_rows)

            # 4b) Element-Screenshots je Befund (best-effort, ~400×400). Die
            # Aufnahme erfolgt bei der Auflösung des Befunds, damit das Element
            # so sichtbar ist wie im Scan-Moment (320 vs. 1920 = anderes Layout);
            # liegt das Element dort außerhalb des Sichtfelds (z. B. geschlossene
            # Mobile-Navigation), versucht die Capture-Routine die anderen
            # Auflösungen.
            await capture_findings_screenshots(
                page, findings_rows, finding_ids, job_id, resolutions[0]
            )

            # 5) Links sammeln → Queue
            await crawler.collect_links(soup, url)

            ok_pages += 1
            pages_done += 1
            est_total = pages_done + len(crawler.queue)
            percent = round(100 * pages_done / est_total) if est_total else 0
            await _update_job(job_id, progress=min(percent, 99), current_url=url, message=f"{pages_done} Seite(n) geprüft")
            # Zeilenumbruch zwischen Seitenzahl und Fehlerzahl: „Seite geprüft: 19"
            # und „Fehler auf dieser Seite: 30" gehören nicht zusammen (StatusLog
            # rendert \n als Umbruch, whitespace-pre-line).
            await _emit(
                job_id, "log", f"Seite geprüft: {pages_done}\nFehler auf dieser Seite: {found}",
                page_url=url, percent=min(percent, 99), page_index=pages_done, page_total=max_pages,
            )

        # Keine einzige Seite erfolgreich geprüft (z. B. Startseite nicht ladbar) →
        # dann nicht als „done" mit 0 Seiten/Befunden durchgehen, sondern klar
        # scheitern. So wirkt ein Scan nie wie ein leeres/persistentes Register.
        if ok_pages == 0:
            msg = "Keine Seite konnte geladen werden — Website nicht erreichbar?"
            await _update_job(job_id, status="failed", error=msg, finished_at=utcnow(), message=msg)
            await _emit(job_id, "error", msg)
            return

        # Erfolgreich abgeschlossen
        # Tote Links (aus dem Crawler) als Pseudo-Test LINKS_404 persistieren,
        # damit sie in by_test/by_url und den Reports erscheinen.
        await _insert_broken_links(job_id, crawler)
        await _update_job(job_id, status="done", progress=100.0, finished_at=utcnow(), message="Scan abgeschlossen")
        await _emit(job_id, "done", "Scan abgeschlossen", percent=100.0, page_total=pages_done)

    except asyncio.CancelledError:
        await _update_job(job_id, status="canceled", finished_at=utcnow(), message="Abgebrochen")
        await _emit(job_id, "status", "Scan abgebrochen")
        raise
    except Exception as exc:  # noqa: BLE001 — Lauf darf nicht den Prozess beenden
        await _update_job(job_id, status="failed", error=str(exc), finished_at=utcnow(), message="Scan fehlgeschlagen")
        await _emit(job_id, "error", f"Scan fehlgeschlagen: {exc}")
    finally:
        broker.close_job(job_id)
        if context is not None:
            try:
                await context.close()
            except Exception:
                pass


async def _run_retest(
    job_id: str,
    job: Job,
    tests: list[dict],
    resolutions: list[int],
    htaccess_user: str | None,
    htaccess_pw: str | None,
) -> None:
    """Führt genau einen Test für genau eine URL aus (Retest aus dem Ergebnis).

    Nutzt denselben Persistenz-/Progress-Pfad wie der Voll-Scan (snapshot,
    pages, findings, WebSocket-Events) — der Mini-Job verhält sich im Frontend
    also wie jeder andere Scan und bleibt reproduzierbar.
    """
    label = ", ".join(t["test_id"] for t in tests)

    # Retest = genau eine Seite: Konsistenz-Checks haben nur eine Signatur und
    # melden daher nichts (kein Vergleich möglich). Trotzdem ein leeres Dict
    # setzen, damit ctx.state nie None ist.
    job_state: dict = {}

    await _snapshot_tests(job_id, tests)
    await _update_job(job_id, status="running", started_at=utcnow(), progress=0.0)
    await _emit(job_id, "status", f"Retest: {label} — {job.url}")

    context = None
    try:
        context, page = await new_context(htaccess_user, htaccess_pw)
        loaded = await _load_page(page, job.url)
        if "error" in loaded:
            await _insert_page(job_id, job.url, None, False, loaded["error"])
            await _update_job(job_id, status="failed", error=loaded["error"],
                              finished_at=utcnow(), message="Retest fehlgeschlagen")
            await _emit(job_id, "error", f"Seite nicht ladbar: {loaded['error']}")
            return

        soup = loaded["soup"]
        http_status = loaded.get("status", 0)
        if http_status and http_status != 200:
            await _insert_page(job_id, job.url, http_status, ok=(http_status < 400), error=None)
            await _update_job(job_id, status="done", progress=100.0, finished_at=utcnow(),
                              message=f"HTTP {http_status} — Seite übersprungen")
            msg = f"HTTP {http_status} — Seite übersprungen"
            await _emit(job_id, "done", msg, percent=100.0, page_total=1)
            return
        await _insert_page(job_id, job.url, http_status, True, None)

        # W3C ist beim Retest nur deaktiviert, wenn es global ausgeschaltet ist
        # (max == 0) — für genau eine Seite ist das sinnvoll, egal wie der
        # Schwellwert des Voll-Scans gesetzt war.
        w3c_active = settings.w3c_validator_max != 0

        rows: list[dict] = []
        for test in tests:
            test_id = test["test_id"]
            if test["type"] == "syntax":
                if test_id in _W3C_TEST_IDS and not w3c_active:
                    continue
                ctx = _make_ctx(job.url, soup, page, None, test_id,
                                htaccess_user, htaccess_pw, w3c_active, True, job_state)
                rows.extend(await _run_check(ctx, test, job.url))
            else:
                for resolution in resolutions:
                    if test.get("desktop_only") and resolution <= settings.keyboard_min_width:
                        continue
                    await page.set_viewport_size({"width": resolution, "height": 1080})
                    await page.wait_for_timeout(150)
                    ctx = _make_ctx(job.url, soup, page, resolution, test_id,
                                    htaccess_user, htaccess_pw, w3c_active, True, job_state)
                    rows.extend(await _run_check(ctx, test, job.url))

        finding_ids = await _insert_findings(job_id, rows)
        await capture_findings_screenshots(
            page, rows, finding_ids, job_id, resolutions[0]
        )
        msg = f"Retest abgeschlossen: {len(rows)} Befund(e)"
        await _update_job(job_id, status="done", progress=100.0, finished_at=utcnow(), message=msg)
        await _emit(job_id, "done", msg, percent=100.0, page_total=1)
    except asyncio.CancelledError:
        await _update_job(job_id, status="canceled", finished_at=utcnow(), message="Abgebrochen")
        await _emit(job_id, "status", "Retest abgebrochen")
        raise
    except Exception as exc:  # noqa: BLE001 — Mini-Job darf den Prozess nicht beenden
        await _update_job(job_id, status="failed", error=str(exc), finished_at=utcnow(),
                          message="Retest fehlgeschlagen")
        await _emit(job_id, "error", f"Retest fehlgeschlagen: {exc}")
    finally:
        broker.close_job(job_id)
        if context is not None:
            try:
                await context.close()
            except Exception:
                pass


def _get_job(job_id: str) -> Job | None:
    with SessionLocal() as session:
        return session.get(Job, job_id)


def _make_ctx(
    url: str,
    soup: Any,
    page: Any,
    resolution: int | None,
    test_id: str,
    htaccess_user: str | None,
    htaccess_pw: str | None,
    w3c_active: bool,
    is_first_page: bool,
    job_state: dict | None = None,
) -> CheckContext:
    return CheckContext(
        url=url,
        soup=soup,
        test_id=test_id,
        page=page,
        resolution=resolution,
        config=settings,
        is_first_page=is_first_page,
        htaccess_user=htaccess_user,
        htaccess_pw=htaccess_pw,
        w3c_enabled=w3c_active,
        w3c_validator_max=settings.w3c_validator_max,
        w3c_validator_url=settings.w3c_validator_url,
        state=job_state,
    )


async def _run_check(ctx: CheckContext, test: dict, url: str) -> list[dict]:
    """Führt einen Check aus und mappt Findings auf DB-Zeilen.

    Stubs (CheckNotImplemented) und Abstürze einzelner Checks brechen den
    Lauf nicht ab — sie werden geloggt bzw. still übersprungen.
    """
    try:
        fn = get_check(ctx.test_id)
    except KeyError:
        return []
    try:
        result = await fn(ctx)
    except CheckNotImplemented:
        return []
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # K1: Abstürze einzelner Checks dürfen den Lauf nicht brechen, aber auch
        # nicht still verschluckt werden — sonst ist ein defekter Check unsichtbar.
        logger.exception("Check %s abgestürzt (URL %s): %s", ctx.test_id, url, exc)
        return []

    meta = {
        "number": test.get("id") or None,
        "category": test.get("category") or None,
        "level": test.get("level") or "SOLLTE",
        "wcag_level": test.get("wcag_level") or None,
        "responsibility": test.get("responsibility") or "technisch",
        "priority": test.get("priority") or "mittel",
    }
    return [
        {
            "test_id": ctx.test_id,
            "url": url,
            "dom_path": f.dom_path or "",
            "message": f.message,
            "detail": f.detail,
            "resolution": f.resolution,
            **meta,
        }
        for f in result
    ]
