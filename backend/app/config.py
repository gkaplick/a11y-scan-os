"""
Zentrale Konfiguration des a11y-Scanners (pydantic-settings).

Werte werden in dieser Reihenfolge aufgelöst:
  1. Defaults unten
  2. Umgebungsvariablen mit Präfix ``A11Y_`` (z. B. ``A11Y_MAX_PAGES=50``)
  3. ``.env``-Datei im Arbeitsverzeichnis

HTACCESS-Zugangsdaten haben bewusst KEINE Defaults — sie kommen pro Job aus
dem Scan-Formular bzw. aus der Umgebung.
"""
from __future__ import annotations

from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="A11Y_",
        env_file=".env",
        extra="ignore",
    )

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Persistenz / Reports ---
    database_path: str = "data/a11y.db"
    output_dir: str = "docs"
    # Element-Screenshots je Befund (je Job ein Unterordner, Dateiname = finding_id)
    screenshots_dir: str = "data/screenshots"

    # --- Scanner / Suiten ---
    default_suite: str = "bitv"               # "bitv" | "wcag" | "all" (bitv + wcag)
    max_parallel_jobs: int = 3                # Semaphore für parallele Scans
    test_resolutions: list[int] = [320, 1920]
    keyboard_min_width: int = 1160            # Fokus-/Keyboard-Tests nur darüber
    w3c_validator_max: int = 1                # 0=aus, -1=alle, N=erste N Seiten

    # --- Crawler ---
    max_pages_per_project: int = 0            # 0 = unbegrenzt
    request_timeout: int = 15                 # Sekunden
    head_timeout: int = 10
    excluded_paths: list[str] = [
        "/admin",
        "/wp-admin",
        "/system",
        "/_api",
        "/node_modules",
    ]
    excluded_extensions: list[str] = [
        # Dokumente
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        # Archive
        ".zip", ".rar", ".tar", ".gz", ".7z",
        # Bilder
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".bmp", ".ico", ".tiff", ".tif",
        # Videos
        ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv",
        # Audio
        ".mp3", ".wav", ".ogg", ".m4a", ".aac",
        # Fonts
        ".woff", ".woff2", ".ttf", ".otf", ".eot",
        # Styles/Scripts
        ".css", ".js", ".map",
    ]

    # --- HTACCESS (optional, KEINE Default-Credentials!) ---
    htaccess_user: str = ""
    htaccess_pw: str = ""

    # --- Login / Session (App-Auth; KEIN Registrierungsweg) ---
    # Erster Admin wird beim Start angelegt, wenn die users-Tabelle leer ist
    # und beide Credentials gesetzt sind. Weitere Zugänge nur über die
    # Verwaltungs-CLI (`python -m app.manage users add …`).
    admin_username: str = ""
    admin_password: str = ""
    session_cookie_name: str = "a11y_session"
    # Secure-Flag nur hinter TLS setzen (prod-Override docker-compose.prod.yml);
    # lokal/ohne HTTPS würde der Browser das Cookie sonst gar nicht speichern.
    session_cookie_secure: bool = False
    session_ttl_hours: float = 24          # Sliding-Session-Lebensdauer
    ws_token_ttl_seconds: int = 300        # Kurzlebiges WS-Ticket (Live-Progress)
    # Explizite CORS-Origins (keine Wildcards). Das SPA läuft same-origin über
    # den Nitro-Proxy — Cross-Origin-Zugriffe sind nicht vorgesehen.
    cors_origins: list[str] = [
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    # --- Browser / Playwright ---
    headless: bool = True
    # Browser beim App-Start warmstarten (best-effort, verkürzt den ersten Job).
    # Im Dev-Modus (--reload) abschalten: der offene Chromium-Prozess hält den
    # Reload-Shutdown auf (uvicorn wartet auf background tasks) → API hängt.
    browser_warmstart: bool = True
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    locale: str = "de-DE"
    timezone_id: str = "Europe/Berlin"

    # --- W3C-Validator (Remote-API) ---
    w3c_validator_url: str = "https://validator.w3.org/nu/?out=json"

    # --- Debug ---
    debug: bool = False

    def should_crawl_url(self, url: str) -> bool:
        """Prüft, ob eine URL gecrawlt werden soll (excluded paths/extensions)."""
        parsed = urlparse(url)
        for excluded in self.excluded_paths:
            if parsed.path.startswith(excluded):
                return False
        for ext in self.excluded_extensions:
            if parsed.path.lower().endswith(ext):
                return False
        return True


settings = Settings()
