"""
Playwright-Browser-Management (async).

Singleton-Chromium mit Anti-Detection-/Stabilitäts-Flags: --no-sandbox,
Cache/Throttling deaktiviert, Init-Scripts für DOM-Pfad-Helfer und
"echter Browser"-Signale.

Jeder Job bekommt einen eigenen Kontext (isolierte Cookies/Cache) mit
optionalen HTACCESS-Credentials — keine geteilten Sessions zwischen Jobs.
"""
from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright

from ..config import settings

# Chromium-Startargumente
_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--disable-web-security",
    "--disable-extensions",
    "--disable-plugins",
    "--disable-images",
    "--disable-javascript-harmony-shipping",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows",
    "--disable-ipc-flooding-protection",
]

# Globale DOM-Pfad-Hilfsfunktion
_DOM_PATH_JS = """
window.getDomPath = function(e){
    var p = [];
    while(e && e.nodeType === 1){
        var tag = e.nodeName.toLowerCase();
        var id  = e.id       ? '#' + e.id                      : '';
        var cls = e.className? '.' + e.className.trim().split(/\\s+/)[0] : '';
        p.unshift(tag + id + cls);
        e = e.parentElement;
    }
    return p.join(' > ');
};
"""

# Anti-Detection-/Browser-Signale
_ANTI_DETECTION_JS = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});
delete window.chrome.runtime.onConnect;
Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8,
});
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8,
});
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});
"""

_browser = None
_pw = None
_lock = asyncio.Lock()


async def get_browser():
    """Singleton-Playwright-Browser starten (idempotent)."""
    global _browser, _pw
    async with _lock:
        if _browser is None or not _browser.is_connected():
            _pw = await async_playwright().start()
            width = settings.test_resolutions[0] if settings.test_resolutions else 1920
            args = list(_LAUNCH_ARGS) + [f"--window-size={width},1080"]
            _browser = await _pw.chromium.launch(
                headless=settings.headless,
                args=args,
            )
        return _browser


async def close_browser() -> None:
    """Browser für Shutdown schließen (timeout-begrenzt, damit der Shutdown
    nie hängen bleibt — z. B. beim uvicorn-Reload im Dev-Modus)."""

    async def _close() -> None:
        global _browser, _pw
        async with _lock:
            if _browser is not None:
                try:
                    await asyncio.wait_for(_browser.close(), timeout=5)
                except Exception:
                    pass
                _browser = None
            if _pw is not None:
                try:
                    await asyncio.wait_for(_pw.stop(), timeout=5)
                except Exception:
                    pass
                _pw = None

    try:
        await asyncio.wait_for(_close(), timeout=8)
    except Exception:
        pass


async def new_context(htaccess_user: str | None = None, htaccess_pw: str | None = None):
    """Isolierter Browser-Kontext für einen Job (inkl. Init-Scripts).

    Aufrufer muss ``await context.close()`` sicherstellen.
    """
    browser = await get_browser()
    creds = (
        {"username": htaccess_user, "password": htaccess_pw}
        if htaccess_user and htaccess_pw
        else None
    )
    width = settings.test_resolutions[0] if settings.test_resolutions else 1920
    context = await browser.new_context(
        http_credentials=creds,
        user_agent=settings.user_agent,
        viewport={"width": width, "height": 1080},
        locale=settings.locale,
        timezone_id=settings.timezone_id,
        extra_http_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
    )
    page = await context.new_page()
    await page.add_init_script(_DOM_PATH_JS)
    await page.add_init_script(_ANTI_DETECTION_JS)
    try:
        session = await context.new_cdp_session(page)
        await session.send("Network.setCacheDisabled", {"cacheDisabled": True})
    except Exception:
        pass  # CDP optional — Fehler sind nicht kritisch
    return context, page
