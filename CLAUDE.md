# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Projektübersicht

**WCAG-BITV2 Barrierefreiheits-Scanner** — Docker-First-Webapp aus FastAPI-Backend (`backend/`) und Nuxt-SPA-Frontend (`frontend/`). Der Scanner crawlt eine Website (BFS, domänen-beschränkt), rendert sie bei **320px und 1920px** und prüft sie gegen **WCAG 2.1** (A/AA/AAA), **BITV 2.0** und **EN 301 549** (Fokus: Websites/Webapps). Ergebnisse: Live-Ansicht im Browser (WebSocket), TXT-Report-Export; Datei-Exporte landen zusätzlich in `docs/`.

> ⚠️ **Wichtig:** Die App ist **keine Quelle der Wahrheit** für die Prüfkriterien. Die normativen Kriterien (Nummern, Level, Beschreibungen, Test-Hinweise) stehen **ausschließlich** in den offiziellen Quellen (W3C/ETSI/BITV) bzw. in `docs/bitvtest/*.json` (BITV-Testnummern). Der Code (`backend/app/engine/registry.py`) ist nur das **maschinelle Abbild** davon und kann Fehler enthalten. **Bevor du Kriterien-Referenzen, Level oder Beschreibungen aus dem Code übernimmst, gegen die offiziellen Quellen prüfen.**

## Commands

```bash
# Start (Docker-First — nichts wird auf dem Host installiert)
docker compose up -d            # → Web http://localhost:3001, API http://localhost:8000 (Swagger: /docs)
docker compose up --build       # nach Änderungen neu bauen
docker compose build            # Images nur bauen
docker compose logs -f api      # Backend-Logs

# Dev-Mode mit Hot Reload (kein Rebuild nötig — Code wird live gemountet)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
#   api: uvicorn --reload (./backend/app live) · web: Nuxt-Dev-Server mit HMR
#   (./frontend live, node_modules aus dem Image). Gleiche URL localhost:3001.
#   Achtung: der Dev-Server lauscht auf Container-Port 3000, damit die Basis-
#   Mapping 3001:3000 greift — im Override KEINEN 3001:3001-Ports-Block
#   hinzufügen (Compose merged ports-Listen additiv → Host-Port-Konflikt).
#   CHOKIDAR_USEPOLLING=true (im Override gesetzt) ist nötig: inotify-Events
#   kommen sonst nicht durch den Docker-Desktop-Bind-Mount → Vite bemerkt
#   Datei-Änderungen nicht, HMR ist tot.

# Tests (pytest im api-Container)
docker compose run --rm api pytest
docker compose run --rm api pytest -m integration     # echter Playwright-Scan der lokalen Test-Fixture
docker compose run --rm api pytest tests/test_registry.py -q

# Tests mit Live-Mount: lokale Änderungen ohne Image-Rebuild
docker compose run --rm -v "G:/Meine Projekte/a11y-scanner/backend:/app" api pytest -q

# Lint (einziges Tooling, flake8 mit E501-Ignore)
docker compose run --rm api flake8 app tests
```

- Reports werden beim Export-Request nach `docs/` geschrieben: `Barrierefreiheit_Report_<domain>_<timestamp>.{pdf,txt,json}`.
- Frontend-Dev ohne Docker: `cd frontend && npm run dev` → http://localhost:3001.
- Ausführliche Architektur-Doku: **`docs/ARCHITEKTUR.md`**.

## Architektur

```
backend/                    # FastAPI + Playwright (Python ≥ 3.11, async)
├── app/
│   ├── main.py             # FastAPI-App, Lifespan (DB-Schema, Browser-Warmstart)
│   ├── config.py           # pydantic-settings, Env-Overrides A11Y_*
│   ├── db.py               # SQLite/SQLAlchemy (sync Engine + SessionLocal)
│   ├── models.py           # ORM: Job, Page, Finding, TestRecord
│   ├── schemas.py          # Pydantic: JobCreate, RetestCreate, JobOut, ResultsOut, …
│   ├── api/                # jobs.py (REST), tests.py (Registry), ws.py (Live-Progress)
│   ├── engine/
│   │   ├── registry.py     # Test-Registry (maschinelles Abbild des Katalogs)
│   │   ├── checks/         # eine Datei pro Test-ID (_base.py, _helpers.py, wcag_1_1_1_img_alt.py, …)
│   │   ├── runner.py       # Scan-Runner (Crawl + Dispatch + Retest-Pfad)
│   │   ├── crawler.py      # BFS-Queue, Domänen-Scoping, 404-Cache
│   │   ├── browser.py      # Playwright-Singleton + isolierte Kontexte
│   │   ├── job_manager.py  # Job-Lebenszyklus + Semaphore
│   │   ├── progress.py     # ProgressBroker für WebSocket-Events
│   │   └── results.py      # Ergebnis-Aggregation (by_test / by_url)
│   └── reports/            # txt_report.py
├── tests/                  # pytest-Suite (Unit + Integration; Fixtures in tests/fixtures/site/)
└── pyproject.toml, requirements.txt, requirements-dev.txt
frontend/                   # Nuxt 4 SPA (ssr: false), Nuxt UI v3, Tailwind v4, Port 3001
├── app/                    # pages/, components/, composables/useScan.js
├── nuxt.config.ts          # routeRules-Proxy /api/** → API_URL; nitro.experimental.websocket:true
└── server/routes/ws/jobs/[id].ts   # crossws-WebSocket-Tunnel zum Backend (ws://api:8000)
data/                       # Docker-Bind-Mount: SQLite (a11y.db)
docs/                       # Report-Exporte + bitvtest-Extrakt + ARCHITEKTUR.md (docs/*.md versioniert)
Dockerfile.api              # API-Image (Playwright-Python-Basis)
Dockerfile.web              # Web-Image (Node multi-stage)
docker-compose.yml          # Services api (8000) + web (3001:3000)
```

## Kernkonzepte

- **Test-Registry** (`engine/registry.py`): `REGISTRY`-Liste von Diktaten — je Eintrag `test_id`, `suite` (`bitv` | `wcag`), `level` (MUSS/SOLLTE/KANN), `wcag_level` (A/AA/AAA), `category`, `wcag`/`bitv`/`en301549`, `responsibility`, `priority`, `type` (`syntax`|`resolution`|`manual`), `desktop_only`, `module` (= `test_id.lower()`, eine Datei pro Test), `check`, `status` (`implemented`|`stub`|`manual`), `description`, `solution`, `test_hint`. Helfer: `get_test()`, `get_tests_for_suite()`, `get_*_tests()`, `validate_registry()`. **`status` wird automatisch abgeleitet**: `engine/checks/__init__.py` leitet ihn beim Import aus dem Check-Quelltext ab (`_sync_registry_status`; implemented ⇔ registrierte Check-Funktion ohne `raise CheckNotImplemented`, `type=manual` bleibt manual). Das Frontend (GET /api/tests + /api/tests/summary) zeigt damit immer den Code-Stand — neue Checks brauchen kein Status-Update.
- **Zwei inhaltliche Suiten**: `bitv` (Default, **vollständige BITV-2.0-Pflicht** — die 98 strukturierten BITV-Prüfschritte plus die zugrunde liegenden WCAG-A/AA-Kriterien, 208 Tests) und `wcag` (optionale WCAG-**AAA**-Zusatzkriterien über die gesetzliche Pflicht hinaus, 28 Tests); die Suite `all` = beide (236 Tests, kompletter Registry). Daneben der Check-Typ `type` (syntax = statisch 1×/Seite, resolution = Playwright pro Auflösung, manual = Checkliste).
- **Check-Schnittstelle** (`engine/checks/_base.py`): `async def check_xxx(ctx: CheckContext) -> list[Finding]`. **Eine Datei pro Test-ID** in `engine/checks/` (`module` = `test_id.lower()`); geteilte Algorithmen (Kontrast, W3C, Label, DOM-Pfad, …) in `_helpers.py`. Syntax-Checks nutzen `ctx.soup` (BeautifulSoup), Resolution-Checks `ctx.page` (Playwright) + `ctx.resolution`. Stubs (`status="stub"`) werfen `CheckNotImplemented` → der Runner verbucht das Kriterium als „noch nicht implementiert". Die Registrierung erfolgt **automatisch**: `engine/checks/__init__.py` baut aus `module` + `check` die `CHECK_FUNCTIONS`-Map.
- **Runner** (`engine/runner.py`): HEAD-Pre-Check → `page.goto` (domcontentloaded + best-effort networkidle) → Syntax-Checks (1×) + Resolution-Checks (pro Auflösung) → Findings persistieren → Links sammeln → Crawler-Queue. Fokus-/Keyboard-Tests nur bei Breite > `keyboard_min_width` (1160 px); W3C-Validator nur für die ersten `w3c_validator_max` Seiten.
- **Retest einzelner Tests** (POST `/api/jobs/retest`): einzelner Befund → Mini-Job (`options.retest=True`, `test_ids=[test_id]`, `resolutions=[resolution]`, `max_pages=1`) → der Runner läuft im schlanken Pfad **ohne Crawl** nur diesen einen Check. Der Endpoint wird per API aufgerufen; einen Retest-Button im Frontend gibt es nicht mehr.
- **Job-Manager** (`engine/job_manager.py`): `asyncio.Semaphore` begrenzt parallele Scans (`max_parallel_jobs`, Default 3); jeder Job ist ein eigener `asyncio.Task`, Zustände `queued → running → done/failed/canceled`.
- **Live-Progress** (`engine/progress.py` + `api/ws.py`): `WS /ws/jobs/{id}` — ProgressBroker mit asyncio-Queue-Subscribern, beim Verbinden mit den letzten Events vorbefüllt. Das Frontend verbindet sich **same-origin** über den crossws-Tunnel (`frontend/server/routes/ws/jobs/[id].ts`), der zum Backend (`ws://api:8000`) verbindet und beidseitig piped. `/ws/**` ist **kein** `routeRules`-Proxy — Nitro-Proxies können WebSocket-Upgrades nicht durchreichen (nur HTTP). **Wichtig:** Ohne `nitro.experimental.websocket: true` in `frontend/nuxt.config.ts` hängt der node-server **keinen** `upgrade`-Listener an (crossws-Adapter wird nicht verdrahtet) und der Tunnel bekommt nie Handshakes → `/ws/**` antwortet mit 426.
- **Echter DOM-Pfad pro Befund**: `_helpers.py` (`_dom_path_at_position` für W3C-Checks) leitet aus der W3C-Zeilenangabe (`lastLine`) per Bisect über newline-offsets + `str(el)`-Suche den echten DOM-Pfad ab (kleinstes überdeckendes Element). `get_dom_path()` in `_base.py` erhält das direkte `body`-Kind im Pfad (`body > main > section > img` statt `body > section > img`). Die W3C-Position bleibt im `detail`-Feld.
- **Crawler** (`engine/crawler.py`): BFS-Queue, nur Links deren netloc in `accepted_domains`; `should_crawl_url()` schließt Pfade/Dateiendungen aus (`excluded_paths`/`excluded_extensions`); HEAD-Requests mit `link_cache` für 404-Erkennung → Pseudo-Test `LINKS_404`.
- **`is_accessible_element()`** filtert `aria-hidden`-Teilbäume — in jeder Element-Schleife verwenden.

## Konventionen

- Identifiers, Kommentare, Commits in **Deutsch**; Check-Funktionen mit Präfix `check_`.
- **Neuen Check anlegen** (ausführlich in `docs/ARCHITEKTUR.md`):
  1. Kriterium in den offiziellen Quellen verifizieren (Level!); BITV-Testnummern gegen `docs/bitvtest/*.json` prüfen,
  2. Check-Funktion in **eigener Datei** `backend/app/engine/checks/<test_id.lower()>.py` schreiben (`async def check_xxx(ctx) -> list[Finding]`); geteilte Algorithmen aus `_helpers.py` importieren,
  3. Registry-Eintrag in `backend/app/engine/registry.py` ergänzen (`module` = `test_id.lower()` + `check` → automatische Registrierung über `engine/checks/__init__.py`),
  4. Suite-Tag setzen (`bitv`/`wcag`) und die Integritätstests laufen lassen (`docker compose run --rm api pytest tests/test_registry.py`).
- **Duplikate vermeiden**: es gibt genau **eine Datei pro Test-ID** (`module` = `test_id.lower()`) — vor einem neuen Check prüfen, ob das Kriterium nicht schon ein Registry-Eintrag mit `module`/`check` ist (geteilte Logik gehört nach `_helpers.py`).
- Code-Stil an den Bestand anpassen (kein striktes Formatierungstool; flake8 mit `E501`-Ignore). Blockierende DB-/`requests`-Aufrufe laufen im async-Kontext über `asyncio.to_thread`.

## Bekannte Probleme / Fallstricke

- **Die App ist kein Source of Truth** — siehe Projektübersicht. Registry-/Check-Level gegen die offiziellen Quellen prüfen, nicht aus dem Code übernehmen.
- W3C-Validator (`validator.w3.org/nu`, remote API) braucht Netz; in eingeschränkten Umgebungen `A11Y_W3C_VALIDATOR_MAX=0`.
- HTACCESS-Zugangsdaten: `config.py` hat **keine Default-Credentials**; Zugangsdaten kommen pro Job aus dem Formular bzw. aus der Umgebung — keine neuen Secrets committen.
- **Kein LICENSE** trotz README-Verweis.
- `.gitignore` ignoriert `docs/*.pdf`, `docs/*.txt` und alle `*.json`, aber **nicht** `*.md` → `docs/*.md` wird versioniert.
- Env-Overrides (pydantic-settings, Präfix `A11Y_`): `A11Y_DEBUG`, `A11Y_MAX_PAGES_PER_PROJECT` (0 = unbegrenzt), `A11Y_W3C_VALIDATOR_MAX` (0=aus, -1=alle, N=erste N Seiten), `A11Y_DATABASE_PATH`, `A11Y_OUTPUT_DIR`, `A11Y_MAX_PARALLEL_JOBS`, `A11Y_DEFAULT_SUITE`, `A11Y_KEYBOARD_MIN_WIDTH`, `A11Y_TEST_RESOLUTIONS` u. a.

## Referenzen

- **BITV-Testnummern (normativ):** `docs/bitvtest/*.json` — die 98 BITV-2.0-Prüfschritte als strukturierte Referenz, angelehnt an die Vorgaben der BITV 2.0 (Quelle der `bitv`-Felder in der Registry; siehe `docs/bitvtest/README.md`)
- **Architektur-Doku (ausführlich):** `docs/ARCHITEKTUR.md`
- **README.md** — Projektübersicht (Schnellstart, Tests, Konfiguration)
- **Offizielle Quellen:** [WCAG 2.1](https://www.w3.org/TR/WCAG21/) · [EN 301 549](https://www.etsi.org/deliver/etsi_en/301500_301599/301549/) · [BITV 2.0](https://www.gesetze-im-internet.de/bitv_2019/)
