"""
Verhaltens-Fixtures für Resolution-Checks (echte Playwright-Seite, per set_content).

- viewport_zoom: maximum-scale=1 (Integer, der Klassiker) und user-scalable=no
  werden erkannt; maximum-scale=1.5 blockiert nicht.
- Kontrast-Gradient: Nicht-Farb-Tokens (to/right) erzeugen keinen Massen-FP —
  schwarzer Text auf weißem Verlauf besteht, weißer Text darauf wird gefunden.

Markiert als integration (nur im Container, dort ist Chromium installiert).
"""
from __future__ import annotations

from bs4 import BeautifulSoup
import pytest

pytest.importorskip("playwright")

from app.engine.checks._base import CheckContext  # noqa: E402
from app.engine.checks.wcag_1_4_10_viewport_zoom import check_viewport_zoom  # noqa: E402
from app.engine.checks.wcag_1_4_3_contrast_aa import check_contrast_min  # noqa: E402


@pytest.fixture
async def page():
    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    browser = await pw.chromium.launch()
    page = await browser.new_page(viewport={"width": 320, "height": 480})
    try:
        yield page
    finally:
        await page.close()
        await browser.close()
        await pw.stop()


def _ctx(page, html: str) -> CheckContext:
    return CheckContext(
        url="https://example.com/",
        soup=BeautifulSoup("", "html.parser"),
        test_id="WCAG_1_4_10_VIEWPORT_ZOOM",
        page=page,
        resolution=320,
        w3c_enabled=False,
    )


# ---------------------------------------------------------- 1.4.10 viewport zoom

@pytest.mark.integration
async def test_viewport_zoom_max_scale_1_detected(page):
    """maximum-scale=1 (Integer ohne Dezimalpunkt) blockiert Zoom → Befund."""
    html = '<meta name="viewport" content="width=device-width, maximum-scale=1">'
    await page.set_content(html)
    findings = await check_viewport_zoom(_ctx(page, html))
    assert len(findings) == 1
    assert findings[0].test_id == "WCAG_1_4_10_VIEWPORT_ZOOM"


@pytest.mark.integration
async def test_viewport_zoom_max_scale_1_0_detected(page):
    html = '<meta name="viewport" content="width=device-width, maximum-scale=1.0">'
    await page.set_content(html)
    assert len(await check_viewport_zoom(_ctx(page, html))) == 1


@pytest.mark.integration
async def test_viewport_zoom_user_scalable_no_detected(page):
    html = '<meta name="viewport" content="width=device-width, user-scalable=no">'
    await page.set_content(html)
    assert len(await check_viewport_zoom(_ctx(page, html))) == 1


@pytest.mark.integration
async def test_viewport_zoom_max_scale_1_5_allows_zoom(page):
    """maximum-scale > 1 schränkt das Reflow nicht ein → kein Befund."""
    html = '<meta name="viewport" content="width=device-width, maximum-scale=1.5">'
    await page.set_content(html)
    assert await check_viewport_zoom(_ctx(page, html)) == []


# ------------------------------------------------------- 1.4.3 Gradient-Kontrast

@pytest.mark.integration
async def test_gradient_white_text_on_white_gradient_detected(page):
    """Weißer Text auf weißem Verlauf → echtes 1:1-Verhältnis → Befund."""
    html = ('<style>p { font-size: 16px; margin: 0; padding: 8px; }</style>'
            '<p style="background: linear-gradient(to right, #ffffff, #ffffff); '
            'color: #ffffff">weiß auf weiß</p>')
    await page.set_content(html)
    findings = await check_contrast_min(_ctx(page, html))
    assert len(findings) == 1
    assert findings[0].test_id == "WCAG_1_4_3_CONTRAST_AA"


@pytest.mark.integration
async def test_gradient_black_text_on_white_gradient_no_fp(page):
    """Schwarzer Text auf weißem Verlauf → 21:1. Die to/right-Tokens dürfen
    keinen künstlichen Schwarz-Befund erzeugen (Massen-FP-Fix)."""
    html = ('<p style="background: linear-gradient(to right, #ffffff, #ffffff); '
            'color: #000000">schwarz</p>')
    await page.set_content(html)
    assert await check_contrast_min(_ctx(page, html)) == []
