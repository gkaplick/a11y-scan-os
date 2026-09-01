"""WCAG 2.1.3 — Tastatur ohne Ausnahme (AAA, Stub). Nur Desktop > 1160px (desktop_only)."""
from __future__ import annotations

from ._base import CheckContext, CheckNotImplemented


async def check_keyboard_enhanced(ctx: CheckContext):
    """WCAG 2.1.3 — Tastaturbedienung auch in Ausnahmefällen (Stub)."""
    raise CheckNotImplemented("WCAG_2_1_3_KEYBOARD_NO_EXCEPT: noch kein Algorithmus")
