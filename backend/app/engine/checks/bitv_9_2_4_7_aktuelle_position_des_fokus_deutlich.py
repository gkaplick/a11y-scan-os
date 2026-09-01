"""BITV_9_2_4_7_AKTUELLE_POSITION_DES_FOKUS_DEUTLICH — Aktuelle Position des Fokus deutlich.

Prüfschritt 9.2.4.7 (bitvtest.de): Der Tastaturfokus muss deutlich
hervorgehoben werden — durch eine eigene Fokusgestaltung des Autors ODER durch
die nicht unterdrückte Standard-Fokushervorhebung des Browsers. Versteckte
Sprunglinks müssen bei Fokuserhalt eingeblendet werden. Bewertet wird nur die
Sichtbarkeit des Fokus, nicht sein Kontrast (das ist 9.1.4.11).

Automatisierbar (Playwright, Tastatur-Modus):
- interaktives Element ohne sichtbaren Fokus-Indikator (outline/box-shadow/
  Farb-/Rahmenwechsel inkl. ::before/::after) → Fokus nicht wahrnehmbar
- unsichtbares Element, das per Tastatur fokussierbar ist → Fokus landet auf
  verstecktem Ziel
- Sprunglink, der bei Fokuserhalt versteckt bleibt

Nicht automatisierbar: Kontrast der Fokushervorhebung (3:1, → 9.1.4.11) und
die Bewertung, ob die Standard-Fokushervorhebung vor gestalteten Hintergründen
gut erkennbar ist.

Seit dem Batching-Umbau (Playwright-Batching): die geteilten Fokus-Bausteine
(Style-Snapshot, Batch-/Chunk-JS) liegen in _helpers.py; hier bleiben nur die
Test-spezifischen Entscheidungen (Schlüsselwörter, Befundtexte).
"""
from __future__ import annotations

from ._base import CheckContext, finding
from ._helpers import (
    DOM_PATH_JS,
    _FOCUS_CHUNK_SIZE,
    _FOCUS_INDICATOR_BATCH_JS,
    _FOCUS_MEASURE_CHUNK_JS,
    _HIDDEN_FOCUSABLE_BATCH_JS,
    _HIDDEN_FOCUS_CHUNK_JS,
    _style_changed,
)

_BITV_TEST_ID = "BITV_9_2_4_7_AKTUELLE_POSITION_DES_FOKUS_DEUTLICH"

_SKIP_KEYWORDS = (
    "skip", "skip to content", "skip to main", "skip navigation",
    "zum hauptinhalt", "zum inhalt", "zum seiteninhalt", "direkt zum inhalt",
    "springe zum inhalt", "hauptinhalt", "sprunglink", "sprung",
)

# --- Sprunglinks: Einblendung bei Fokuserhalt ------------------------------

_IN_VIEWPORT_JS = """(el) => {
    if (!el || el.getClientRects().length === 0) { return false; }
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') { return false; }
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0
        && r.bottom > 0 && r.right > 0
        && r.top < window.innerHeight && r.left < window.innerWidth;
}"""

# Vorphase in EINEM evaluate: Sprunglink-Merkmale (text/cls/id) + Sichtbarkeit.
_SKIPLINK_BATCH_JS = (
    "() => {\n"
    "    const inViewport = " + _IN_VIEWPORT_JS + ";\n"
    "    const domPath = " + DOM_PATH_JS + ";\n"
    "    const nodes = document.querySelectorAll(\"a[href^='#']\");\n"
    "    const out = [];\n"
    "    for (let i = 0; i < nodes.length; i++) {\n"
    "        const el = nodes[i];\n"
    "        try {\n"
    "            let cls = '';\n"
    "            const c = el.className;\n"
    "            if (typeof c === 'string') { cls = c; }\n"
    "            else if (c && c.baseVal) { cls = c.baseVal; }\n"
    "            out.push({\n"
    "                index: i,\n"
    "                text: (el.textContent || '').trim().toLowerCase(),\n"
    "                cls: cls.toLowerCase(),\n"
    "                id: (el.id || '').toLowerCase(),\n"
    "                inViewport: inViewport(el),\n"
    "            });\n"
    "        } catch (e) {}\n"
    "    }\n"
    "    return out;\n"
    "}"
)

# Gechunkte Fokusprobe: fokussieren, 100 ms warten, erneut Sichtbarkeit prüfen.
_SKIPLINK_FOCUS_CHUNK_JS = (
    "async (candidates) => {\n"
    "    const nodes = document.querySelectorAll(\"a[href^='#']\");\n"
    "    const sleep = (ms) => new Promise(r => setTimeout(r, ms));\n"
    "    const inViewport = " + _IN_VIEWPORT_JS + ";\n"
    "    const domPath = " + DOM_PATH_JS + ";\n"
    "    const out = [];\n"
    "    for (const c of candidates) {\n"
    "        const el = nodes[c.index];\n"
    "        if (!el) continue;\n"
    "        try {\n"
    "            el.focus();\n"
    "            await sleep(100);\n"
    "            out.push({ index: c.index, inViewport: inViewport(el), path: domPath(el) });\n"
    "        } catch (e) {}\n"
    "        finally {\n"
    "            try { el.blur(); } catch (e) {}\n"
    "        }\n"
    "    }\n"
    "    return out;\n"
    "}"
)


# --- Fokus-Indikator (Tastatur-Modus) --------------------------------------

async def _pruefe_fokus_indikator(page, errors: list) -> None:
    """Jedes fokussierbare Element braucht einen sichtbaren Fokus-Indikator."""
    candidates = await page.evaluate(_FOCUS_INDICATOR_BATCH_JS)
    for start in range(0, len(candidates), _FOCUS_CHUNK_SIZE):
        chunk = candidates[start:start + _FOCUS_CHUNK_SIZE]
        results = await page.evaluate(_FOCUS_MEASURE_CHUNK_JS, chunk)
        by_index = {r["index"]: r for r in results}
        for cand in chunk:
            r = by_index.get(cand["index"])
            if r is None:
                continue
            try:
                changed = any(_style_changed(a, b) for a, b in zip(r["inactive"], r["focused"]))
            except Exception:
                continue  # wie im Original: Stil-Analyse-Fehler überspringt den Kandidaten
            if not changed:
                errors.append(finding(
                    _BITV_TEST_ID,
                    f"<{cand['node']}> ohne sichtbaren Fokus-Indikator bei Tastaturfokus",
                    cand["path"],
                ))


async def _pruefe_versteckte_fokussierbare(page, errors: list) -> None:
    """Kein Element darf unsichtbar sein und trotzdem den Tastaturfokus erhalten."""
    candidates = await page.evaluate(_HIDDEN_FOCUSABLE_BATCH_JS)
    for start in range(0, len(candidates), _FOCUS_CHUNK_SIZE):
        chunk = candidates[start:start + _FOCUS_CHUNK_SIZE]
        for info in await page.evaluate(_HIDDEN_FOCUS_CHUNK_JS, chunk):
            desc = info["tagName"]
            if info["id"]:
                desc += f"#{info['id']}"
            elif info["className"]:
                desc += f".{info['className'].split(' ')[0]}"
            errors.append(finding(
                _BITV_TEST_ID,
                f"{desc} fokussierbar, aber nicht sichtbar "
                f"(display={info['display']}, opacity={info['opacity']})",
                info["path"],
            ))


async def _pruefe_sprunglinks(page, errors: list) -> None:
    """Sprunglinks müssen bei Fokuserhalt eingeblendet werden."""
    anchors = await page.evaluate(_SKIPLINK_BATCH_JS)
    candidates = []
    for a in anchors:
        combined = f"{a['text']} {a['cls']} {a['id']}"
        if not any(kw in combined for kw in _SKIP_KEYWORDS):
            continue
        if a["inViewport"]:
            continue  # ohnehin sichtbar → kein Einblend-Erfordernis
        candidates.append(a)
    for start in range(0, len(candidates), _FOCUS_CHUNK_SIZE):
        chunk = candidates[start:start + _FOCUS_CHUNK_SIZE]
        for r in await page.evaluate(_SKIPLINK_FOCUS_CHUNK_JS, chunk):
            if not r["inViewport"]:
                errors.append(finding(
                    _BITV_TEST_ID,
                    "Sprunglink bleibt bei Fokuserhalt versteckt",
                    r["path"],
                ))


async def check_aktuelle_position_des_fokus_deutlich(ctx: CheckContext):
    """BITV 9.2.4.7 — Fokus-Indikator, versteckte Fokusziele, eingeblendete Sprunglinks."""
    page = ctx.page
    if page is None:
        # Nur als Resolution-Check mit Playwright-Seite aussagekräftig; in
        # Unit-Tests (ctx ohne page) kein Befund.
        return []

    errors: list = []
    await _pruefe_fokus_indikator(page, errors)
    await _pruefe_versteckte_fokussierbare(page, errors)
    await _pruefe_sprunglinks(page, errors)
    return errors
