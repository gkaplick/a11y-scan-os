"""
Async-Crawler (BFS) mit Domänen-Scope, Exclusions und Link-404-Cache.

Der BFS-Zustand lebt in einer ``Crawler``-Instanz; die eigentliche
Seiten-Verarbeitung
(Playwright-Load + Checks) übernimmt der Runner — der Crawler liefert
genau die Teile, die er kann: URL-Normalisierung, Link-Sammlung, Queue,
404-Prüfung mit Cache.
"""
from __future__ import annotations

import asyncio
from collections import deque
from urllib.parse import urlparse, urljoin

from ..config import settings


def normalize_url(url: str) -> str:
    """Normalisiert eine URL für konsistente Vergleiche.

    - Domain → lowercase
    - trailing slash entfernen (außer bei root)
    - Fragment (#anchor) entfernen
    - Query bleibt erhalten
    """
    if not url:
        return url
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path
    if path.endswith("/") and len(path) > 1:
        path = path[:-1]
    normalized = f"{parsed.scheme}://{netloc}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized


def dedupe_key(url: str) -> str:
    """Identität einer URL für die Besuchs-Queue: nur Host (ohne www.) + Pfad.

    User-Vorgabe: „beachtet wird lediglich die Domain mit dem folgenden Pfad."
    http/https und www./non-www. sind damit dieselbe Seite — sonst würde
    dieselbe Seite doppelt gecrawlt, nur weil Protokoll oder www.-Präfix
    abweichen. Query/Fragment zählen nicht (Tracking-Parameter, Anker).
    """
    if not url:
        return url
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path
    if path.endswith("/") and len(path) > 1:
        path = path[:-1]
    if not path:
        path = "/"
    return f"{netloc}{path}"


def _make_session(htaccess_user: str | None, htaccess_pw: str | None):
    """requests.Session für HEAD-Prüfungen (verify=False, optional Basic-Auth)."""
    import requests

    session = requests.Session()
    session.verify = False
    if htaccess_user and htaccess_pw:
        session.auth = (htaccess_user, htaccess_pw)
    session.headers.update(
        {"User-Agent": settings.user_agent}
    )
    return session


class Crawler:
    """BFS-Zustand + Link-/404-Logik für einen einzelnen Job."""

    def __init__(
        self,
        start_url: str,
        max_pages: int | None = None,
        htaccess_user: str | None = None,
        htaccess_pw: str | None = None,
    ) -> None:
        self.settings = settings
        domain = urlparse(start_url).netloc
        base_domain = domain[4:] if domain.startswith("www.") else domain
        self.accepted_domains = {domain, base_domain, f"www.{base_domain}"}
        start = normalize_url(start_url)
        self.queue: deque[str] = deque([start])
        # visited/queued_urls speichern den dedupe_key (nur Host ohne www. + Pfad),
        # damit http/https- und www./non-www.-Varianten derselben Seite nur
        # einmal in die Queue gelangen (User-Vorgabe).
        self.queued_urls: set[str] = {dedupe_key(start)}
        self.visited: set[str] = set()
        self.max_pages = max_pages or settings.max_pages_per_project or None

        # Link-404-Cache (über den ganzen Lauf)
        self.link_cache: dict[str, dict] = {}
        self.cache_stats = {"hits": 0, "misses": 0, "total": 0}

        self.pages_404: list[tuple[str, str]] = []      # (404-url, gefunden-unter)
        self.broken_links: dict[str, list[str]] = {}     # page_url -> [broken]

        self._session = _make_session(htaccess_user, htaccess_pw)

    # --- Queue / Besuch ---

    def has_more(self) -> bool:
        return bool(self.queue)

    def next_url(self) -> str | None:
        while self.queue:
            url = self.queue.popleft()
            normalized = normalize_url(url)
            if dedupe_key(normalized) not in self.visited:
                return normalized
        return None

    def mark_visited(self, url: str) -> None:
        self.visited.add(dedupe_key(url))

    def should_enqueue(self, url: str) -> bool:
        """Interne URL, noch nicht besucht/gequeued und crawler-fähig?"""
        normalized = normalize_url(url)
        key = dedupe_key(normalized)
        if key in self.visited or key in self.queued_urls:
            return False
        if not self.settings.should_crawl_url(normalized):
            return False
        parsed = urlparse(normalized)
        return parsed.netloc in self.accepted_domains

    def enqueue(self, url: str) -> None:
        normalized = normalize_url(url)
        key = dedupe_key(normalized)
        if key not in self.visited and key not in self.queued_urls:
            self.queue.append(normalized)
            self.queued_urls.add(key)

    # --- Link-Sammlung + 404-Prüfung ---

    async def collect_links(self, soup, page_url: str) -> list[str]:
        """Sammelt Links der Seite: queued interne URLs + 404-Check aller Links.

        Gibt die internen Links zurück, die in die Queue kamen (für Status-Meldungen).
        """
        queued_new: list[str] = []
        links_to_check: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a.get("href") or ""
            if href.startswith(("tel:", "mailto:", "javascript:", "#")):
                continue
            full_link = urljoin(page_url, href)
            full_normalized = normalize_url(full_link)

            if not self.settings.should_crawl_url(full_normalized):
                continue

            if self.should_enqueue(full_normalized):
                self.enqueue(full_normalized)
                queued_new.append(full_normalized)

            links_to_check.add(full_normalized)

        await self._check_links(links_to_check, page_url)
        return queued_new

    async def _check_links(self, links: set[str], page_url: str) -> None:
        """HEAD-Check aller Links mit Cache; 404-Ergebnisse speichern."""
        if not links:
            return
        self.cache_stats["total"] += len(links)
        broken: list[str] = []

        for full_link in links:
            if full_link in self.link_cache:
                self.cache_stats["hits"] += 1
                if self.link_cache[full_link]["status"] == 404:
                    broken.append(full_link)
                continue

            self.cache_stats["misses"] += 1
            try:
                status = await asyncio.to_thread(
                    self._head_check, full_link
                )
                self.link_cache[full_link] = {"status": status}
                if status == 404:
                    broken.append(full_link)
            except Exception:
                self.link_cache[full_link] = {"status": "error"}

        if broken:
            self.broken_links[page_url] = sorted(set(broken))

    def _head_check(self, url: str) -> int:
        """Blockierender HEAD-Request (läuft via to_thread)."""
        resp = self._session.head(url, allow_redirects=True, timeout=1)
        return resp.status_code

    async def head_info(self, url: str) -> tuple[int, str]:
        """HEAD-Request mit Status + Content-Type (für den Pre-Check vor page.goto)."""
        return await asyncio.to_thread(self._head_info, url)

    def _head_info(self, url: str) -> tuple[int, str]:
        resp = self._session.head(url, allow_redirects=True, timeout=10)
        return resp.status_code, resp.headers.get("content-type", "")

    def is_404(self, url: str) -> bool:
        return url in self.pages_404

    def note_404(self, url: str, found_on: str) -> None:
        self.pages_404.append((url, found_on))
