"""WCAG 2.1.2 — keine Tastaturfalle (nur Desktop > 1160px, desktop_only).

Fix (Review): die Quick-Variante (positive tabindex auf Folgeseiten als
"Tastaturfalle" melden) ist entfernt — das ist WCAG 2.4.3, kein 2.1.2
(Doppelbefund). Es läuft immer der vollständige Tab-Schleifen-Test.

Seit dem Batching-Umbau: die Sammlung der fokussierbaren Elemente in EINEM
evaluate (_TRAP_COLLECT_JS), die Tab-Schleife bleibt sequenziell (inherent).
"""
from __future__ import annotations

from ._base import CheckContext, finding
from ._helpers import (
    _CLEANUP_JS,
    _FOCUSABLE_SELECTOR,
    _TRAP_COLLECT_JS,
    _TRAP_STEP_JS,
)


async def check_keyboard_trap(ctx: CheckContext):
    """WCAG 2.1.2 — algorithmischer Tastaturfallen-Test (Tab-Schleife)."""
    page = ctx.page
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
                        "WCAG_2_1_2_KEYBOARD_TRAP",
                        f"Tastaturfalle: zurück zu bereits besuchtem Element '{info['tag']}' "
                        f"bei Tab-Schritt {step}",
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
