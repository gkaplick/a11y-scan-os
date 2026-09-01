"""WCAG 1.4.11 — Kontrast nicht-textueller Inhalte (UI-Komponenten).

Port des implementierten BITV-Checks 9.1.4.11 (gleicher Algorithmus,
anderer test_id). Automatisierter Teil des Kriteriums: Bedienelemente,
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

_TEST_ID = "WCAG_1_4_11_NON_TEXT_CONTRAST"


async def check_contrast_ui(ctx: CheckContext):
    """WCAG 1.4.11 — Bedienelement-Rahmen mit < 3:1 Kontrast."""
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
