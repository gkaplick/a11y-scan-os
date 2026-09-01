"""BITV_9_2_1_2_KEINE_TASTATURFALLE — Keine Tastaturfalle.

Übernommen aus WCAG_2_1_2_KEYBOARD_TRAP (vollständiger Tab-Schleifen-Test):
der Tastaturfokus wird durch die fokussierbaren Elemente der Seite getabbt.
Kehrt der Fokus dabei zu einem bereits besuchten Element zurück, kann er nicht
wegbewegt werden — eine Tastaturfalle liegt vor (BITV: "Kann der
Tastaturfokus auf ein Element der Seite bewegt werden, muss er auch von diesem
Element wieder wegbewegt werden können.").

Hinweis: Der Check benötigt eine echte Playwright-Seite (ctx.page). Der
Registry-Eintrag in bitv_steps.py führt den Test noch als type="syntax";
Fokus-/Tastaturtests müssen als type="resolution" (+ desktop_only) laufen.
Seit dem Batching-Umbau: Sammlung in EINEM evaluate (_TRAP_COLLECT_JS),
Tab-Schleife sequenziell.
"""
from __future__ import annotations

from ._base import CheckContext, Finding, finding
from ._helpers import (
    _CLEANUP_JS,
    _FOCUSABLE_SELECTOR,
    _TRAP_COLLECT_JS,
    _TRAP_STEP_JS,
)


async def check_keine_tastaturfalle(ctx: CheckContext) -> list[Finding]:
    """BITV_9_2_1_2 — algorithmischer Tastaturfallen-Test (Tab-Schleife)."""
    page = ctx.page
    if page is None:
        return []
    errors = []

    focusables = (await page.evaluate(_TRAP_COLLECT_JS))["indices"]

    if len(focusables) >= 2:
        await page.locator(_FOCUSABLE_SELECTOR).nth(focusables[0]).focus()
        await page.wait_for_timeout(100)
        for step in range(len(focusables) + 1):
            try:
                result = await page.evaluate(_TRAP_STEP_JS)
                if result and result.get("skipLink"):
                    continue
                if result and result.get("trapDetected"):
                    info = result["element"]
                    errors.append(finding(
                        "BITV_9_2_1_2_KEINE_TASTATURFALLE",
                        f"Tastaturfalle: zurück zu bereits besuchtem Element '{info['tag']}' "
                        f"bei Tab-Schritt {step} — Fokus kann nicht wegbewegt werden",
                        info["path"],
                    ))
                    break
                if step < len(focusables):
                    await page.keyboard.press("Tab")
                    await page.wait_for_timeout(150)
            except Exception:
                break
        await page.evaluate(_CLEANUP_JS)
    return errors
