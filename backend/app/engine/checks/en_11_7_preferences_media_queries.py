"""EN 301 549 11.7 — Präferenzen: Medien-/Animations-Präferenzen (Stub).

Das Kriterium verlangt eine Abschaltbarkeit von Bewegung durch Interaktion
(analog WCAG 2.3.3) — nicht nur das Vorhandensein von
``prefers-reduced-motion``-Media-Queries. Ein eigenes Vorhaben; als "nicht
implementiert" geführt.
"""
from __future__ import annotations

from ._base import CheckContext, CheckNotImplemented


async def check_prefers_media_queries(ctx: CheckContext):
    """EN 301 549 11.7 — Bewegung per Präferenz/Interaktion abschaltbar (Stub)."""
    raise CheckNotImplemented(
        "EN_11_7_PREFERENCES_MEDIA_QUERIES: kein Algorithmus — bloße prefers-*-"
        "Existenz ist nicht das Kriterium (Abschaltbarkeit von Bewegung)"
    )
