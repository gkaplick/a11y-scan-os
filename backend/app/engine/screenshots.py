"""
Element-Screenshots für Befunde: ~400×400-PNG mit roter Outline.

Beim Scan wird je Befund das betroffene Element im Browser markiert (rote
Outline, 3 px + 2 px Offset) und als 400×400-Ausschnitt des Viewports
festgehalten. Die PNGs liegen unter ``<screenshots_dir>/<job_id>/<finding_id>.png``
und werden über ``GET /api/jobs/{job_id}/screenshots/{finding_id}`` ausgeliefert —
das Frontend zeigt sie als 80×80-Thumbnail mit Lightbox (Zoom auf das Original).

Kann der Locator des Elements nicht aufgelöst werden (Element weg, verdeckt,
unsichtbar, Pseudo-Befunde wie LINKS_404, ungültiger Selektorkurzschluss),
wird kein Screenshot geschrieben — ein fehlendes Thumbnail ist nie ein
Scan-Fehler.

Koordinaten-Hinweis: ``page.screenshot(clip=...)`` ist für Einzel-Seiten-
Screenshots **viewport-relativ** (empirisch verifiziert, nicht seiten-relativ).
Deshalb wird das Element zuerst zentriert ins Sichtfeld gescrollt und der
Ausschnitt direkt aus der (viewport-relativen) ``bounding_box`` abgeleitet,
an die Viewport-Ränder geklemmt. An schmalen Viewports (320 px) wird der
Ausschnitt entsprechend schmaler — das Element bleibt aber immer sichtbar.

Bekannte Grenze: Der Browser startet mit ``--disable-images`` (Scan-Performance) —
Elemente, die selbst ein Bild sind, können daher leer erscheinen; die rote
Outline macht das betroffene Element trotzdem sichtbar.
"""
from __future__ import annotations

import os

from ..config import settings

# Zielgröße des Screenshots (Klassengröße der Lightbox im Frontend)
SIZE = 400


def screenshots_root() -> str:
    """Wurzelverzeichnis für alle Element-Screenshots (je Job ein Ordner)."""
    return os.path.abspath(settings.screenshots_dir)


def job_screenshot_dir(job_id: str) -> str:
    return os.path.join(screenshots_root(), job_id)


def finding_screenshot_path(job_id: str, finding_id: int) -> str:
    return os.path.join(job_screenshot_dir(job_id), f"{finding_id}.png")


def _clip_around(box: dict, viewport: dict, size: int = SIZE) -> dict | None:
    """400×400-Ausschnitt um den Element-Mittelpunkt (viewport-Koordinaten).

    Der Clip wird an die Viewport-Ränder geklemmt; durch das vorherige
    zentrierte Scrollen liegt das Element im Sichtfeld und damit immer im
    geklemmten Ausschnitt. None, wenn die Box zu klein ist (unsichtbar).
    """
    if not box or box["width"] < 2 or box["height"] < 2:
        return None
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    x = max(0.0, min(cx - size / 2, max(0, viewport["width"] - size)))
    y = max(0.0, min(cy - size / 2, max(0, viewport["height"] - size)))
    return {"x": x, "y": y, "width": size, "height": size}


async def capture_element_screenshot(page, dom_path: str, out_path: str) -> str:
    """Markiert das Element mit roter Outline und speichert den Ausschnitt.

    Best-effort, Rückgabe-Zustände für den Aufrufer:
      - ``"ok"``        → Screenshot geschrieben
      - ``"offcanvas"`` → Element liegt außerhalb des Sichtfelds (Element-
        Mittelpunkt nach dem Scrollen außerhalb des Viewports, z. B. Nav-Link
        im geschlossenen Mobile-Menü, das nicht ins Sichtfeld scrollbar ist) —
        der Aufrufer versucht dann eine andere Auflösung
      - ``"fail"``      → Locator nicht auflösbar oder Element unsichtbar

    Die Outline wird in jedem Fall wieder entfernt (finally).
    """
    locator = page.locator(dom_path).first
    try:
        await locator.evaluate(
            "el => el.scrollIntoView({ block: 'center', inline: 'center' })"
        )
        await page.wait_for_timeout(60)  # Scroll-Rendering abwarten
    except Exception:
        return "fail"
    box = await locator.bounding_box()
    if not box or box["width"] < 2 or box["height"] < 2:
        return "fail"
    viewport = await page.evaluate(
        "() => ({ width: window.innerWidth, height: window.innerHeight })"
    )
    # Off-Canvas-Erkennung: liegt der Element-Mittelpunkt außerhalb des
    # Viewports, kann der Ausschnitt das Element nicht zeigen (bei schmalen
    # Viewports ist die Seite horizontal oft nicht scrollbar → scrollIntoView
    # kann das Element nicht ins Sichtfeld holen, der Clip würde den
    # Viewport-Rand/Anfang zeigen statt des Elements).
    cx = box["x"] + box["width"] / 2
    cy = box["y"] + box["height"] / 2
    if cx < 0 or cx >= viewport["width"] or cy < 0 or cy >= viewport["height"]:
        return "offcanvas"
    clip = _clip_around(box, viewport)
    if clip is None:
        return "fail"
    try:
        await locator.evaluate(
            "el => { el.style.outline = '3px solid #ef4444';"
            " el.style.outlineOffset = '2px'; }"
        )
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        await page.screenshot(path=out_path, clip=clip)
        return "ok"
    finally:
        try:
            await locator.evaluate(
                "el => { el.style.outline = ''; el.style.outlineOffset = ''; }"
            )
        except Exception:
            pass


async def capture_findings_screenshots(
    page,
    rows: list[dict],
    ids: list[int],
    job_id: str,
    default_resolution: int,
) -> None:
    """Zeichnet je Befund mit DOM-Pfad einen Element-Screenshot (best-effort).

    Gruppiert nach Befund-Auflösung: Für jede betroffene Breite wird der
    Viewport einmal gesetzt, dann alle Befunde dieser Breite aufgenommen
    (Syntax-Befunde ohne ``resolution``-Feld bei der ersten Auflösung).
    Fehlende Screenshots sind nie ein Fehler — sie erscheinen im Frontend
    einfach ohne Thumbnail.
    """
    by_res: dict[int, list[tuple[int, str]]] = {}
    for row, fid in zip(rows, ids):
        dom_path = row.get("dom_path")
        if not dom_path:
            continue
        res = row.get("resolution") or default_resolution
        by_res.setdefault(res, []).append((fid, dom_path))

    off_canvas: list[tuple[int, str]] = []
    for res, items in by_res.items():
        try:
            await page.set_viewport_size({"width": res, "height": 1080})
            await page.wait_for_timeout(120)
        except Exception:
            continue
        for fid, dom_path in items:
            try:
                status = await capture_element_screenshot(
                    page, dom_path, finding_screenshot_path(job_id, fid)
                )
                if status == "offcanvas":
                    off_canvas.append((fid, dom_path))
            except Exception:
                pass

    # Off-Canvas-Nachzüge: Elemente, die bei ihrer Auflösung nicht im Sichtfeld
    # lagen (z. B. Nav-Links im geschlossenen Mobile-Menü bei 320 px), werden
    # noch bei den übrigen Auflösungen versucht — der Befund bekommt so einen
    # Screenshot, sobald sein Element irgendwo sichtbar ist.
    if off_canvas:
        for fid, dom_path in off_canvas:
            for res in settings.test_resolutions:
                try:
                    await page.set_viewport_size({"width": res, "height": 1080})
                    await page.wait_for_timeout(120)
                except Exception:
                    continue
                try:
                    status = await capture_element_screenshot(
                        page, dom_path, finding_screenshot_path(job_id, fid)
                    )
                except Exception:
                    continue
                if status == "ok":
                    break
