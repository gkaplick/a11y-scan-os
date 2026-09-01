"""
Tests der Element-Screenshots (engine/screenshots.py) und der Screenshot-
Bausteine im Runner.

- _clip_around: reine Geometrie (400×400 um das Element, an den Viewport geklemmt)
- _insert_findings liefert DB-IDs (Basis der Screenshot-Dateinamen)
- FindingOut trägt die Finding-ID (Frontend baut daraus die Screenshot-URL)
"""
from __future__ import annotations

from app.db import SessionLocal
from app.engine.checks._base import get_dom_path
from app.engine.results import _vorhandene_screenshot_ids, build_results
from app.engine.runner import _insert_findings
from app.engine.screenshots import _clip_around, finding_screenshot_path, job_screenshot_dir
from app.models import Finding, Job


# --- _clip_around: reine Geometrie ---


def test_clip_around_zentriert_um_element():
    box = {"x": 100, "y": 200, "width": 200, "height": 100}
    viewport = {"width": 1920, "height": 1080}
    clip = _clip_around(box, viewport)
    # 400×400 um den Element-Mittelpunkt (200, 250) → x 0..400, y 50..450
    assert clip == {"x": 0, "y": 50, "width": 400, "height": 400}


def test_clip_around_schmaler_viewport_wird_geklemmt():
    box = {"x": 200, "y": 300, "width": 100, "height": 50}
    viewport = {"width": 320, "height": 600}
    clip = _clip_around(box, viewport)
    # 400 > 320 → x auf 0 geklemmt; y zentriert um 325 → 125..525
    assert clip["x"] == 0
    assert clip["width"] == 400
    assert clip["y"] == 125
    assert clip["y"] + clip["height"] <= viewport["height"]


def test_clip_around_unsichtbar_liefert_none():
    assert _clip_around(None, {"width": 1920, "height": 1080}) is None
    assert (
        _clip_around({"x": 0, "y": 0, "width": 0, "height": 0}, {"width": 1920, "height": 1080})
        is None
    )


def test_clip_around_element_am_rand_bleibt_im_viewport():
    box = {"x": 100, "y": 1040, "width": 50, "height": 50}
    viewport = {"width": 1920, "height": 1080}
    clip = _clip_around(box, viewport)
    assert clip["y"] == 1080 - 400
    assert clip["y"] + clip["height"] <= viewport["height"]


# --- DOM-Pfad: Geschwisterindex (eindeutiger Locator für Screenshots) ---


def test_get_dom_path_geschwisterindex_fuer_eindeutigkeit():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        "<body><main><ul><li>Eins</li><li>Zwei</li><li>Drei</li></ul>"
        "<img src='x'><p>Absatz</p></main></body>",
        "html.parser",
    )
    zweites_li = soup.find_all("li")[1]
    assert get_dom_path(zweites_li) == "body > main > ul > li:nth-of-type(2)"
    # Einzelne Geschwister (img/p) und eindeutige Pfade bekommen KEINEN Index
    img = soup.find("img")
    assert get_dom_path(img) == "body > main > img"


def test_get_dom_path_mit_id_kein_index():
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        "<body><main><section id='a'></section><section id='b'></section></main></body>",
        "html.parser",
    )
    zweite = soup.find_all("section")[1]
    # id macht den Pfad bereits eindeutig → kein :nth-of-type
    assert get_dom_path(zweite) == "body > main > section#b"


# --- Screenshot-Verfügbarkeit (Frontend zeigt nur vorhandene Thumbnails) ---


def test_vorhandene_screenshot_ids_liest_png_dateien():
    import os

    job_id = "job-shots-vorhanden"
    verzeichnis = job_screenshot_dir(job_id)
    os.makedirs(verzeichnis, exist_ok=True)
    for name in ("1.png", "2.png", "README.txt", "abc.png", "03.png"):
        with open(os.path.join(verzeichnis, name), "w") as fh:
            fh.write("x")

    assert _vorhandene_screenshot_ids(job_id) == {1, 2, 3}
    # Fehlender Ordner → leere Menge, kein Fehler
    assert _vorhandene_screenshot_ids("gibt-es-nicht") == set()


# --- _insert_findings liefert IDs (Screenshot-Dateinamen) ---


async def test_insert_findings_liefert_ids(db_session):
    job_id = "job-shots"
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done"))
    db_session.commit()

    rows = [
        {"test_id": "WCAG_1_1_1_IMG_ALT", "url": "https://example.com/", "dom_path": "body > img#a",
         "message": "Bild ohne alt", "resolution": None, "number": "1.1.1", "category": "WCAG",
         "level": "MUSS", "wcag_level": "A", "responsibility": "redaktionell", "priority": "hoch"},
        {"test_id": "WCAG_1_1_1_IMG_ALT", "url": "https://example.com/", "dom_path": "body > img#b",
         "message": "Bild ohne alt", "resolution": None, "number": "1.1.1", "category": "WCAG",
         "level": "MUSS", "wcag_level": "A", "responsibility": "redaktionell", "priority": "hoch"},
    ]
    ids = await _insert_findings(job_id, rows)
    assert len(ids) == 2
    assert ids[0] != ids[1]  # echte Auto-Increment-IDs
    assert all(isinstance(i, int) and i > 0 for i in ids)

    # Dateiname leitet sich aus der ID ab
    assert finding_screenshot_path(job_id, ids[0]).endswith(f"{ids[0]}.png")
    assert finding_screenshot_path(job_id, ids[1]).endswith(f"{ids[1]}.png")

    # persistiert (Reihenfolge = Einfügereihenfolge)
    with SessionLocal() as session:
        stored = session.query(Finding).filter_by(job_id=job_id).order_by(Finding.id).all()
    assert [f.id for f in stored] == ids
    assert [f.dom_path for f in stored] == [r["dom_path"] for r in rows]


async def test_insert_findings_leer_liefert_leere_liste():
    assert await _insert_findings("job-leer", []) == []


# --- FindingOut trägt die ID (Basis der Frontend-Screenshot-URL) ---


async def test_finding_out_traegt_id(db_session):
    job_id = "job-id-out"
    db_session.add(Job(id=job_id, url="https://example.com/", suite="bitv", status="done"))
    db_session.add(Finding(job_id=job_id, test_id="WCAG_1_1_1_IMG_ALT", url="https://example.com/",
                           dom_path="body > img", message="Bild ohne alt", resolution=None,
                           number="1.1.1", category="WCAG", level="MUSS", wcag_level="A",
                           responsibility="redaktionell", priority="hoch"))
    db_session.commit()

    results = await build_results(job_id)
    assert results is not None
    assert results.job_id == job_id

    f = results.by_test[0].findings[0]
    assert f.id > 0
    assert f.dom_path == "body > img"
    # kein Screenshot-File im Test → Flag False (kein Thumbnail, kein 404)
    assert f.screenshot is False

    # Screenshot-Datei angelegt → Flag dreht auf True (Thumbnail erscheint)
    import os
    png = finding_screenshot_path(job_id, f.id)
    os.makedirs(os.path.dirname(png), exist_ok=True)
    with open(png, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
    results2 = await build_results(job_id)
    assert results2.by_test[0].findings[0].screenshot is True
