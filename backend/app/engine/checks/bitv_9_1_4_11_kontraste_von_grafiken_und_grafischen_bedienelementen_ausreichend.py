"""BITV 9.1.4.11 — Kontraste von Grafiken und grafischen Bedienelementen.

Automatisierter Teil des bitvtest-Prüfschritts (Punkt 2.2): Bedienelemente,
die nur über ihren Rahmen als solche erkennbar sind, brauchen einen
Rahmenkontrast von 3:1 gegen die umgebende Fläche. Gemessen wird der
Rahmen gegen den effektiven Hintergrund (Element-Füllung, auf die Seite
alpha-geblendet).

Ob eine Grafik oder ein Icon Information trägt (und damit kontrastpflichtig
ist), ist ohne Semantik nicht zuverlässig maschinell entscheidbar — Grafiken
bleiben der manuellen Sichtprüfung. Der Check misst ausschließlich den
objektiv messbaren Rahmenkontrast von input/select/textarea/button
(Resolution-Check: benötigt die effektiven Computed Styles).
"""
from __future__ import annotations

from ._base import CheckContext, finding
from ._helpers import _non_text_contrast_batch, contrast

_TEST_ID = "BITV_9_1_4_11_KONTRASTE_VON_GRAFIKEN_UND_GRAFISCHEN_BEDIENELEMENTEN_AUSREICHEND"


async def check_kontraste_von_grafiken_und_grafischen_bedienelementen_ausreichend(ctx: CheckContext):
    """BITV 9.1.4.11 — Bedienelement-Rahmen mit < 3:1 Kontrast."""
    errors = []
    for data in await _non_text_contrast_batch(ctx.page):
        ratio = contrast(data["border"], data["background"])
        if ratio >= 3.0:
            continue
        errors.append(finding(
            _TEST_ID,
            f"Bedienelement-Rahmen nur {ratio:.2f}:1 (erfordert 3:1) — "
            "Kontrolle wäre ohne Rahmen nicht als Bedienelement erkennbar",
            data["path"],
            ctx.resolution,
        ))
    return errors
