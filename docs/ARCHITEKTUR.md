# Architektur — A11Y Accessibility Scanner

> Ausführliche technische Doku zum WCAG-BITV2 Barrierefreiheits-Scanner. Kurzfassung und Arbeits-Konventionen: `CLAUDE.md`. Normative Prüfkriterien: `docs/bitvtest/*.json` (BITV-Testnummern) und die offiziellen Quellen (W3C/ETSI/BITV).

## 1. Zielbild

Der Scanner ist eine **Docker-First-Webapp**:

- **Backend** (`backend/`): asynchroner **FastAPI**-Service mit Playwright (Chromium), SQLite-Persistenz, REST-API und WebSocket-Live-Progress. Er übernimmt Crawl, Check-Ausführung, Retest und Report-Erzeugung.
- **Frontend** (`frontend/`): **Nuxt 4 SPA** (ssr: `false`) mit Nuxt UI v3 / Tailwind v4. URL-Formular, Job-Liste, Live-Status (WS), Ergebnis-Ansicht mit Filtern sowie eine Test-Abdeckungs-Map.
- **Docker-First**: Es wird nichts auf dem Host installiert. `docker compose up` startet beide Services; Playwright-Chromium ist im API-Image gebündelt.

Scan-Umfang: Crawl (BFS, domänen-beschränkt), Rendering bei **320px und 1920px**, Prüfung gegen **WCAG 2.1 / BITV 2.0 / EN 301 549**, Export als TXT-Report.

## 2. Verzeichnisstruktur

```
a11y-scanner/
├── backend/                        # FastAPI + Playwright (Python ≥ 3.11, async)
│   ├── app/
│   │   ├── main.py                 # FastAPI-App + Lifespan (DB-Schema, Browser-Warmstart)
│   │   ├── config.py               # pydantic-settings (Settings), Env-Overrides A11Y_*
│   │   ├── db.py                   # SQLite-Engine, SessionLocal, init_db()
│   │   ├── models.py               # ORM: Job, Page, Finding, TestRecord
│   │   ├── schemas.py              # Pydantic: JobCreate, RetestCreate, JobOut, ResultsOut, …
│   │   ├── api/
│   │   │   ├── jobs.py             # REST-Endpunkte für Scans (inkl. Retest + TXT-Export)
│   │   │   ├── tests.py            # Registry-Endpunkte (Katalog + Summary)
│   │   │   └── ws.py               # WebSocket /ws/jobs/{id}
│   │   ├── engine/
│   │   │   ├── registry.py         # Test-Registry (maschinelles Abbild des Katalogs)
│   │   │   ├── checks/             # eine Datei pro Test-ID (module = test_id.lower())
│   │   │   │   ├── _base.py        # CheckContext, Finding, CheckNotImplemented, Helfer
│   │   │   │   ├── _helpers.py     # geteilte Algorithmen (Kontrast, W3C, Label, DOM-Pfad, …)
│   │   │   │   ├── __init__.py     # get_check()-Dispatch (baut CHECK_FUNCTIONS aus Registry)
│   │   │   │   ├── wcag_1_1_1_img_alt.py, wcag_1_4_3_contrast_aa.py, wcag_2_4_1_skip_links.py,
│   │   │   │   ├── en_7_2_1_ad_playback.py, en_11_7_preferences.py, bitv_7_declaration.py,
│   │   │   │   ├── …               # je Registry-Eintrag (siehe 3.7: 60 Dateien)
│   │   │   ├── runner.py           # Scan-Runner (Crawl + Dispatch + Retest-Pfad)
│   │   │   ├── crawler.py          # BFS-Queue, Domänen-Scoping, Link-404-Cache
│   │   │   ├── browser.py          # Playwright-Singleton, isolierte Job-Kontexte
│   │   │   ├── job_manager.py      # Job-Lebenszyklus + Semaphore (max_parallel_jobs)
│   │   │   ├── progress.py         # ProgressBroker (WS-Events, Recent-Puffer)
│   │   │   └── results.py          # Ergebnis-Aggregation (by_test / by_url)
│   │   └── reports/                # txt_report.py
│   ├── tests/                      # pytest-Suite
│   │   ├── conftest.py             # Env vor app.*-Import, saubere DB, Fixtures
│   │   ├── test_job_manager.py     # Lifecycle + Semaphore (Fake-Runner)
│   │   ├── test_results.py         # by_test/by_url-Aggregation
│   │   ├── test_reports.py         # Smoke-Tests TXT
│   │   ├── test_registry.py        # Registry-Integrität + Check-Auflösung
│   │   ├── test_retest.py          # Retest-Anlage + W3C-Position→DOM-Pfad
│   │   ├── test_integration.py     # voller Scan einer lokalen Fixture (marker: integration)
│   │   └── fixtures/site/          # index.html, kontakt.html
│   ├── pyproject.toml              # Projekt (v3.0.0), Dependencies, pytest-Konfig
│   ├── requirements.txt            # Laufzeit-Deps (playwright gepinnt aufs Basis-Image)
│   └── requirements-dev.txt        # + pytest, pytest-asyncio, httpx, flake8
├── frontend/                       # Nuxt 4 SPA (ssr: false), Nuxt UI v3, Tailwind v4
│   ├── app/
│   │   ├── app.vue                 # Shell (Header/Nav/Footer)
│   │   ├── pages/
│   │   │   ├── index.vue           # URL-Formular + Test-Abdeckungs-Map
│   │   │   └── jobs/
│   │   │       ├── index.vue       # Job-Liste
│   │   │       └── [id].vue        # Live-Status (WS) + Ergebnis (Filter, Export)
│   │   ├── components/             # UrlForm, ProgressPanel, StatusLog, ResultByTest,
│   │   │                           # ResultByUrl, CoverageMap
│   │   └── composables/useScan.js  # REST- + WS-Client (same-origin)
│   ├── nuxt.config.ts              # routeRules-Proxy /api/** → API_URL
│   └── server/routes/ws/jobs/[id].ts   # crossws-WebSocket-Tunnel zum Backend
├── data/                           # Docker-Bind-Mount: SQLite (a11y.db)
├── docs/                           # Report-Exporte (TXT) + bitvtest-Katalog + ARCHITEKTUR.md
├── Dockerfile.api                  # API-Image (mcr.microsoft.com/playwright/python)
├── Dockerfile.web                  # Web-Image (Node 22 multi-stage)
├── docker-compose.yml              # Services api + web
└── .gitignore                      # ignoriert docs/*.{pdf,txt,json}, *.db, .nuxt, …
```

## 3. Backend

### 3.1 FastAPI-App (`app/main.py`)

- Startet im **Lifespan**: `init_db()` (legt alle Tabellen idempotent an), `ensure_admin()` (Env-Bootstrap des Erst-Admins, siehe „Session-Auth-Architektur“) und best-effort `get_browser()` (Playwright-Warmstart; wird bei Bedarf pro Job ohnehin gestartet). Beim Shutdown: `close_browser()`.
- Routen-Module: `api/auth.py`, `api/jobs.py`, `api/tests.py`, `api/ws.py`.
- CORS ist auf `settings.cors_origins` (explizite Liste, Default lokal `localhost:3001`) + `allow_credentials=True` beschränkt. Im Produktiv-Container ist das Frontend ohnehin **same-origin** über den Nitro-Proxy — dort ist CORS kein Angriffsweg.
- `GET /` liefert einen kleinen Service-Index; `GET /api/health` → `{"status": "ok"}` (beide offen).

### 3.2 Konfiguration (`app/config.py`, pydantic-settings)

Alle Werte sind als `Settings`-Felder deklariert und werden in dieser Reihenfolge aufgelöst: Default → Umgebungsvariable (Präfix `A11Y_`) → `.env`. Wichtige Felder:

| Feld | Env | Default | Bedeutung |
|---|---|---|---|
| `database_path` | `A11Y_DATABASE_PATH` | `data/a11y.db` | SQLite-Datei |
| `output_dir` | `A11Y_OUTPUT_DIR` | `docs` | Report-Exporte |
| `default_suite` | `A11Y_DEFAULT_SUITE` | `bitv` | `bitv` \| `wcag` \| `all` |
| `max_parallel_jobs` | `A11Y_MAX_PARALLEL_JOBS` | `3` | Semaphore paralleler Scans |
| `test_resolutions` | `A11Y_TEST_RESOLUTIONS` | `[320, 1920]` | Renderbreiten |
| `keyboard_min_width` | `A11Y_KEYBOARD_MIN_WIDTH` | `1160` | Fokus-/Keyboard-Tests nur darüber |
| `w3c_validator_max` | `A11Y_W3C_VALIDATOR_MAX` | `1` | 0=aus, -1=alle, N=erste N Seiten |
| `max_pages_per_project` | `A11Y_MAX_PAGES_PER_PROJECT` | `0` | 0 = unbegrenzt |
| `htaccess_user` / `htaccess_pw` | `A11Y_HTACCESS_USER` / `A11Y_HTACCESS_PW` | `""` | **keine Default-Credentials** |
| `admin_username` / `admin_password` | `A11Y_ADMIN_USERNAME` / `A11Y_ADMIN_PASSWORD` | `""` | Env-Bootstrap des Erst-Admins (nur bei leerer `users`-Tabelle) |
| `session_cookie_name` | `A11Y_SESSION_COOKIE_NAME` | `a11y_session` | Name des Session-Cookies |
| `session_cookie_secure` | `A11Y_SESSION_COOKIE_SECURE` | `False` | `Secure`-Flag auf dem Cookie (Prod hinter TLS: `true`) |
| `session_ttl_hours` | `A11Y_SESSION_TTL_HOURS` | `24` | Lebensdauer einer Session |
| `ws_token_ttl_seconds` | `A11Y_WS_TOKEN_TTL_SECONDS` | `300` | Lebensdauer eines WS-Tickets |
| `cors_origins` | `A11Y_CORS_ORIGINS` | `http://localhost:3001, http://127.0.0.1:3001` | erlaubte Origins (SPA ist same-origin über den Nitro-Proxy; Liste deckt direkte API-Dev-Zugriffe ab) |

`Settings.should_crawl_url(url)` prüft die `excluded_paths`/`excluded_extensions`.

### 3.3 Persistenz (`app/db.py`, `app/models.py`)

- **SQLAlchemy 2.0**, bewusst **synchron** (Engine + `SessionLocal`); async-Zugriffe laufen über `asyncio.to_thread`. Bei sehr vielen Findings kann später auf `aiosqlite` + async Session umgestellt werden.
- Tabellen:
  - `Job` — id (uuid), url, suite, `options` (JSON: max_pages, retest, test_ids, resolutions, htaccess…), `status` (queued/running/done/failed/canceled), `progress`, current_url, message, error, Zeitstempel.
  - `Page` — je gecrawlte URL (http_status, ok, error, visited_at).
  - `Finding` — je Verstoß: test_id, url, **dom_path**, message, detail, resolution, plus **denormalisierte** Registry-Metadaten (wcag, bitv, en301549, level, wcag_level, responsibility, priority) — Stand des Laufs.
  - `TestRecord` — **Snapshot** des Registry-Stands pro Job (Reports bleiben so reproduzierbar).
  - `User` — Login-Konto (`username` unique, `password_hash` bcrypt). Kein Registrierungsweg.
  - `AuthSession` — aktive Session: nur **SHA-256-Hash** des Cookie-Tokens, `user_id`, `expires_at`. Wird per Logout sofort widerrufen, abgelaufene Sitzungen opportunistisch gelöscht.
  - `WsToken` — kurzlebiges **Einmal-Ticket** (SHA-256-Hash) für den WebSocket (siehe 3.5): nach erfolgreichem Konsum sofort gelöscht.
- Neue Tabellen entstehen über SQLAlchemy `create_all` beim Start (`main.py`-Lifespan) — es gibt keine Migrationen.
- `conftest.py` setzt `A11Y_DATABASE_PATH`/`A11Y_OUTPUT_DIR` auf temporäre Pfade, `A11Y_W3C_VALIDATOR_MAX=0` und `A11Y_BROWSER_WARMSTART=false`, damit Tests isoliert und ohne externe W3C-Aufrufe/Playwright-Warmstart laufen. `_clean_db` leert zusätzlich `WsToken`/`AuthSession`/`User` (Kinder zuerst).

### 3.4 REST-API

Alle Endpunkte (außer WS) unter Prefix `/api`. **Zugriffsschutz:** Alle Router
`/api/jobs`, `/api/tests` (und `/api/auth`) außer `/login` sind über
`dependencies=[Depends(require_user)]` bzw. `Depends(require_user)` pro Endpoint
**session-geschützt** — der Router-Dependency-Mechanismus greift auch vor
`FileResponse`-Downloads (Screenshots, TXT-Export). Nur `/api/health` bleibt
offen (Betrieb/Orchestrierung). Ohne gültiges Session-Cookie → `401`.

| Methode | Pfad | Schutz | Zweck |
|---|---|---|---|
| `POST` | `/api/auth/login` | offen (Limiter) | Login, setzt Session-Cookie, liefert `UserOut` |
| `POST` | `/api/auth/logout` | Session | widerruft Session + leert Cookie |
| `GET` | `/api/auth/me` | Session | aktueller Benutzer (Frontend-Reload prüft hiermit) |
| `GET` | `/api/auth/ws-token` | Session | kurzlebiges Einmal-Ticket für den WS-Live-Progress |
| `POST` | `/api/jobs` | Session | Scan anlegen (`JobCreate`: url, suite, max_pages, htaccess_user/pw) |
| `GET` | `/api/jobs` | Session | Job-Liste (neueste zuerst, `limit` 1–200) |
| `GET` | `/api/jobs/{id}` | Session | Einzelner Job (mit page_count/finding_count) |
| `DELETE` | `/api/jobs/{id}` | Session | Scan abbrechen (cancel); 409 wenn nicht mehr abbrechbar |
| `GET` | `/api/jobs/{id}/results` | Session | Ergebnis (`ResultsOut`: by_test / by_url / tests / manual_tests / stub_tests) |
| `GET` | `/api/jobs/{id}/export/txt` | Session | TXT-Report-Download **und** zusätzlich als Datei nach `docs/` |
| `POST` | `/api/jobs/retest` | Session | **Retest** eines einzelnen Tests für eine URL (Mini-Job) |
| `GET` | `/api/tests` | Session | Kompletter Katalog (`TestOut[]`), filterbar nach suite/status |
| `GET` | `/api/tests/summary` | Session | Aggregierte Kennzahlen (total, by_status, by_suite, by_category, by_level) |
| `GET` | `/api/tests/{test_id}` | Session | Einzelner Katalog-Eintrag |
| `GET` | `/api/health` | offen | Health-Check |
| `WS` | `/ws/jobs/{id}` | WS-Ticket (`?ws_token=`) | Live-Progress (siehe 3.5) |

**Retest-Endpunkt** (`POST /api/jobs/retest`): Body `RetestCreate { url, test_id, resolution }`. Validiert, dass der Test im Registry existiert (404) und nicht `manual` ist (422 — manuelle Kriterien lassen sich nicht automatisiert erneut ausführen). Erzeugt über `job_manager.create_retest(url, test_id, suite, resolution)` einen Mini-Job und gibt ihn als `JobOut` zurück.

**Export-Endpunkt**: erzeugt den TXT-Report aus dem kanonischen `ResultsOut`, schreibt die Datei zusätzlich nach `settings.output_dir` (Dateiname `Barrierefreiheit_Report_<domain>_<timestamp>.txt`) und liefert sie als `Content-Disposition: attachment` zurück.

#### Session-Auth-Architektur (`app/security.py`, `app/api/auth.py`, `app/manage.py`)

**Grundsatz:** Backend-eigene Session-Auth, kein Registrierungsweg — Konten legt
ausschließlich der Betreiber an. Es gibt **zwei** Anlegewege:

- **Env-Bootstrap** (`security.ensure_admin`): wird im Lifespan nach `init_db()`
  aufgerufen. Legt genau dann einen Admin an, wenn die `users`-Tabelle **leer**
  ist und `A11Y_ADMIN_USERNAME`/`A11Y_ADMIN_PASSWORD` gesetzt sind. Danach sind
  die Env-Werte wirkungslos (Tabelle nicht mehr leer) — sie können also nach dem
  ersten Start wieder entfernt werden.
- **CLI** (`app/manage.py`): `python -m app.manage users add|list|set-password|remove`
  im api-Container. Bewusst nur DB-/Config-Importe (startet schnell); Passwort
  per `--password` oder `getpass`-Prompt; validiert das 72-Byte-bcrypt-Limit.

**Session-Fluss (REST):**
1. `POST /api/auth/login` prüft ein **In-Memory-Rate-Limit** (`_LoginLimiter`,
   pro Client-IP: 5 Versuche / 15 min, dann 15 min Sperre), führt bei unbekanntem
   Benutzernamen trotzdem einen **bcrypt-Vergleich gegen einen Dummy-Hash** aus
   (gleiche Laufzeit → keine Benutzernamen-Enumeration über Timing) und antwortet
   bei Fehlern immer mit **derselben** Meldung „Ungültige Zugangsdaten.“.
2. Bei Erfolg wird ein opaker Token (`secrets.token_urlsafe(48)`) erzeugt; in der
   DB (`AuthSession`) liegt nur der **SHA-256-Digest**. Der Client bekommt den
   Rohwert ausschließlich als **`httpOnly`-Cookie** (`a11y_session`, SameSite=Lax,
   `Secure` über `A11Y_SESSION_COOKIE_SECURE`, `path=/`).
3. Jeder geschützte Endpoint hängt an `require_user` (FastAPI-Dependency): Cookie →
   Digest-Lookup → Ablaufprüfung (**sliding Renewal**: `expires_at` wird bei jedem
   Zugriff um die TTL nach hinten geschoben) → `401 „Nicht angemeldet"`.
4. `POST /api/auth/logout` löscht die Session sofort (Revoke) und leert das Cookie.
   Abgelaufene Sitzungen werden bei Gelegenheit gelöscht (opportunistischer Purge).

**Warum keine Cookie-Auth für den WebSocket:** Der Nitro-Tunnel
(`frontend/server/routes/ws/jobs/[id].ts`) reicht ans Backend **nur Pfad + Query**
weiter; der Node-`WebSocket`-Client kann keinen `Cookie`-Header setzen. Deshalb
holt die SPA über die Session ein **kurzlebiges Einmal-Ticket**
(`GET /api/auth/ws-token`, TTL `ws_token_ttl_seconds`=300) und hängt es als
`?ws_token=…` an. `WsToken` speichert ebenfalls nur den SHA-256-Digest; nach
erfolgreichem Konsum wird die Zeile **gelöscht** (Single-Use). Der WS-Handler
validiert das Ticket **nach `accept()` und vor `subscribe()`**; ungültig →
`close(1008)` + Return. Ein verlorenes/verbrauchtes Ticket fällt über den
bestehenden `onClose → REST-Polling`-Pfad ab (kein Funktionsverlust, nur kein
Live-Update).

**bcrypt im async-Kontext:** `hash_password`/`verify_password` (bcrypt direkt,
Cost 12, 72-Byte-Limit, dummy-vergleich) laufen im Runner- und Request-Pfad über
`asyncio.to_thread` — Cost 12 ≈ 100–300 ms dürfen den Event-Loop nicht blockieren.

### 3.5 WebSocket-Protokoll (`api/ws.py`, `engine/progress.py`)

- **`ProgressBroker`** (In-Process): pro Job eine Menge von `asyncio.Queue`-Subscribern (eine Queue pro Client). Zusätzlich werden die letzten N Events pro Job behalten (`deque(maxlen=500)`), damit ein später beigetretener Client sofort den aktuellen Stand erhält.
- **Auth:** Der Handler akzeptiert, validiert dann das `?ws_token=`-Einmal-Ticket (siehe „Session-Auth-Architektur“) und subscribed erst danach die Queue — ungültiges/verbrauchtes Ticket → `close(1008)`, kein Zugriff auf Job-Events.
- `ProgressEvent`-Felder: `type` (`page` | `stage` | `status` | `done` | `error` | `log`), `job_id`, `percent`, `page_url`, `page_index`, `page_total`, `resolution`, `message`, `at`. Bei `done`/`error` schließt der Client typischerweise selbst.
- **Frontend-Tunnel**: Das Browser-Frontend verbindet sich same-origin auf `:3001`. `/ws/**` ist **kein** `routeRules`-Proxy (Nitro-Proxy kann keine WebSocket-Upgrades), sondern eine eigene Nitro-Server-Route `frontend/server/routes/ws/jobs/[id].ts` mit h3 `defineWebSocketHandler` (crossws): Sie öffnet eine Client-WebSocket-Verbindung zum selben Pfad auf `ws://api:8000` und piped Nachrichten in beide Richtungen. Schlägt die Upstream-Verbindung fehl, wird das Browser-Socket sauber geschlossen, sodass `useScan.js` über `onClose` auf REST-Polling zurückfällt.
- **⚠️ Voraussetzung `experimental.websocket`**: Damit Nitros node-server-Produktion tatsächlich `upgrade`-Events an crossws weiterreicht, muss in `frontend/nuxt.config.ts` `nitro: { experimental: { websocket: true } }` gesetzt sein. Ohne dieses Flag bleibt `import.meta._websocket` falsy, der crossws-`handleUpgrade`-Listener wird nie registriert und `/ws/**` antwortet auf Handshakes mit **426 Upgrade Required** (die Route existiert im Build, bekommt aber keine Upgrades). Symptom eines verpassten Flips: Der Browser-Log zeigt `WebSocket connection to 'ws://localhost:3001/ws/jobs/…' failed`.

### 3.6 Test-Registry (`engine/registry.py`)

Zentrale, maschinenlesbare Beschreibung **aller** Prüfkriterien. `REGISTRY` ist eine **Liste von Diktaten**. Felder je Eintrag:

| Feld | Bedeutung |
|---|---|
| `id` | Kriterien-Nummer (WCAG-Nr. oder EN-/BITV-Nr.) |
| `test_id` | eindeutige maschinenlesbare ID |
| `title` | deutscher Kurztitel |
| `suite` | `bitv` (Default, **vollständige BITV-2.0-Pflicht**: die 98 BITV-Prüfschritte plus die zugrunde liegenden WCAG-A/AA-Kriterien, 208 Tests) \| `wcag` (optionale WCAG-AAA-Zusatzkriterien über die Pflicht hinaus, 28 Tests) |
| `level` | BITV-Kategorie: MUSS / SOLLTE / KANN |
| `wcag_level` | WCAG-2.1-Level: A / AA / AAA (`""` bei reinen EN-Tests) |
| `category` | Standard-Kategorie: BITV / WCAG / EN 301 549 (nach normgebendem Standard, Präfix `BITV_`/`WCAG_`/`EN_`) |
| `wcag` | WCAG-Kriterien-Nummer (z. B. `1.1.1`) oder `""` |
| `bitv` | **BITV-2.0-Testnummer** — Kapitel-9-Nummer (z. B. `9.1.1.1b`) **oder** EN-301-549-Kapitel 5/6/7/11/12 (z. B. `5.2`, `11.7`). `""` bei reinen WCAG-AAA-Kriterien (kein BITV-Prüfschritt). Quelle: `docs/bitvtest/*.json` |
| `en301549` | EN-301-549-Kapitel (z. B. `7.2.1`) oder `""` |
| `responsibility` | technisch \| redaktionell |
| `priority` | hoch \| mittel \| niedrig |
| `type` | `syntax` (statisch, 1×/Seite) \| `resolution` (Playwright pro Auflösung) \| `manual` |
| `desktop_only` | `true` für Fokus-/Keyboard-Tests → laufen nur bei Breite > `keyboard_min_width` (Default `false`) |
| `module` | Dateiname (ohne `.py`) in `engine/checks/` — **eine Datei pro Test**: `test_id.lower()` (z. B. `WCAG_1_1_1_IMG_ALT` → `wcag_1_1_1_img_alt`) |
| `check` | Funktionsname im Modul (`None` bei manual) |
| `status` | `implemented` (echter Algorithmus) \| `stub` (architektiert, wirft `CheckNotImplemented`) \| `manual` |
| `description` | Was geprüft wird |
| `solution` | Lösungsvorschlag |
| `test_hint` | Hinweise für den Test |

Helfer: `get_test(test_id)`, `get_tests_for_suite(suite)` (`all` = alles), `get_syntax_tests` / `get_resolution_tests` / `get_manual_tests` / `get_implemented_tests` / `get_stub_tests`, und `validate_registry()` → Liste von Warnungen (wird von pytest als Integritäts-Check genutzt).

**Suiten-Semantik:** Die Registry ist partitioniert in

- `bitv` (**208 Tests**) — die **vollständige BITV-2.0-Pflicht**: die 98 strukturierten BITV-Prüfschritte plus die zugrunde liegenden WCAG-A/AA-Kriterien (Default-Suite). Das ist der komplette Pflichtumfang der Level **A und AA**.
- `wcag` (**28 Tests**) — ausschließlich optionale **WCAG-Level-AAA-Zusatzkriterien** über die gesetzliche Pflicht hinaus.
- `all` (**236 Tests**) — der komplette Registry (beide Suiten zusammen).

Die Bewertung läuft quer durch die Suiten in drei gleichrangigen Systemen (**BITV · WCAG · EN 301 549**): Jedes Kriterium trägt genau eine Kategorie und eine Nummer; EN 301 549 erbt die Ergebnisse der BITV-/WCAG-Kriterien.

Ein Scan mit `default_suite=bitv` (Default) prüft also den vollen Pflichtumfang A/AA; `suite=all` schließt zusätzlich die freiwilligen AAA-Kriterien ein.

> Das Registry ist das **maschinelle Abbild** der normativen Prüfkriterien. **BITV-Testnummern** stammen aus `docs/bitvtest/*.json` (angelehnt an die Vorgaben der BITV 2.0). Normativ sind die offiziellen Quellen (W3C/ETSI/BITV) — Registry-Metadaten (Level, Referenzen) sind gegen diese zu prüfen, nicht aus dem Code zu übernehmen.

### 3.7 Check-Schnittstelle (`engine/checks/`)

**Kontrakt**: jeder Check ist eine async-Funktion

```python
async def check_xxx(ctx: CheckContext) -> list[Finding]
```

- `CheckContext` (aus `_base.py`): `url`, `soup` (BeautifulSoup), `test_id`, `page` (Playwright, nur bei resolution), `resolution`, `config` (Settings), `is_first_page`, `htaccess_user`/`htaccess_pw`, `w3c_enabled`, `w3c_validator_max`, `w3c_validator_url`.
- `Finding` (Dataclass): `test_id`, `message`, `dom_path`, `resolution`, `detail`. Komfort-Factory: `finding(...)`.
- Syntax-Checks nutzen `ctx.soup` und laufen **1× pro Seite**; Resolution-Checks nutzen `ctx.page` + `ctx.resolution` und laufen **pro Auflösung**.
- **Stubs** (`status="stub"`) existieren bereits mit der Signatur, werfen aber `CheckNotImplemented` — der Runner verbucht das Kriterium als „noch nicht implementiert" statt als Fehler.
- **Helfer** in `_base.py`:
  - `get_dom_path(tag)` — baut den Pfad bis `body` auf und **erhält das direkte body-Kind** im Pfad (`body > main > section > img`), inkl. `#id`/`.klasse`-Suffixen.
  - `is_accessible_element(element)` — filtert `aria-hidden`-Teilbäume (inkl. Eltern-Kette). In jeder Element-Schleife verwenden.
- **Dispatch** (`engine/checks/__init__.py`): baut beim Import aus jedem Registry-Eintrag mit `module`+`check` die Map `CHECK_FUNCTIONS` (test_id → Funktion). Auflösungsfehler (ImportError/AttributeError) landen in `MISSING_CHECKS` (sichtbar für Tests statt still zu schweigen). `get_check(test_id)` schlägt die Funktion nach.

### 3.8 Runner-Ablauf (`engine/runner.py`)

`run_job(job_id)` wird als `asyncio.Task` vom Job-Manager gestartet.

**Voll-Scan:**
1. Job aus DB lesen; `options`/`suite`/`resolutions` auflösen.
2. **Retest-Flow?** Falls `options.retest` → `_run_retest` (siehe unten), sonst weiter.
3. Test-Auswahl via `reg.get_tests_for_suite(suite)`; Snapshot aller Tests als `TestRecord`; Status → `running`.
4. Browser-Kontext (`new_context(htaccess_user, htaccess_pw)`) + `Crawler(start_url, max_pages)`.
5. **Seiten-Loop** (`while crawler.has_more()`):
   - HEAD-Pre-Check (`head_info`): Nicht-HTTP-200 wird übersprungen/notiert (404 → Pseudo-Test), Nicht-HTML übersprungen.
   - `page.goto` (domcontentloaded) + best-effort networkidle → `soup`.
   - Syntax-Checks (1×, `ctx.soup`) und Resolution-Checks (pro Auflösung, `page.set_viewport_size` + 150 ms). Tests mit `desktop_only=True` (Fokus/Keyboard) nur bei Breite > `keyboard_min_width`. W3C-Tests (`WCAG_4_1_1_*`) nur für die ersten `w3c_validator_max` Seiten.
   - Findings persistieren (mit denormalisierten Registry-Metadaten), Links sammeln (`crawler.collect_links`), Queue füllen, `progress`/Events emittieren.
6. Abschluss: tote Links als `LINKS_404` persistieren, Status → `done`, `done`-Event.
7. Fehlerbehandlung: `CancelledError` → `canceled`; sonstige Exceptions → `failed` (+ `error`-Event); `finally`: Broker aufräumen, Kontext schließen.

**Retest-Pfad (`_run_retest`):**
- Kein Crawl, keine Link-Sammlung. Lädt **genau eine URL**, führt **nur die ausgewählten Checks** aus (Syntax 1×, Resolution pro `resolutions`-Liste aus den Mini-Job-Optionen).
- Nutzt denselben Persistenz-/Progress-Pfad wie der Voll-Scan (Snapshot, Page, Findings, WS-Events) — der Mini-Job verhält sich im Frontend wie jeder andere Scan und bleibt reproduzierbar.
- W3C ist beim Retest aktiv, wenn `w3c_validator_max != 0` (für genau eine Seite unabhängig vom Schwellwert des Voll-Scans).
- `_run_check` schluckt `CheckNotImplemented` und einzelne Check-Abstürze (bricht den Lauf nicht ab).

### 3.9 Job-Manager & Semaphore (`engine/job_manager.py`)

- `JobManager` ist ein Singleton (`job_manager`). Jeder Job wird als `asyncio.create_task` unter der Semaphore (`max_parallel_jobs`, Default 3) gestartet.
- `create_job` setzt die Standard-Optionen (max_pages, htaccess, resolutions); `create_retest` setzt `retest=True`, `test_ids=[test_id]`, `resolutions=[resolution]` (bzw. Default-Auflösungen), `max_pages=1`.
- `cancel_job`: queued-Jobs hinter der Semaphore werden direkt als `canceled` markiert; laufende Jobs über `task.cancel()` (der Runner setzt im `CancelledError`-Handler `status=canceled`).

### 3.10 Crawler (`engine/crawler.py`)

- BFS-Queue mit `normalize_url` (lowercase-Domain, trailing slash ohne Root, Fragment entfernt, Query bleibt).
- Domänen-Scope: `accepted_domains` = Startdomain, Basis-Domain und `www.`-Variante.
- `should_crawl_url` (aus Settings) schließt `excluded_paths`/`excluded_extensions` aus.
- HEAD-Requests mit `link_cache` (über den ganzen Lauf) → `broken_links` (Seite → defekte Ziele) für den Pseudo-Test `LINKS_404`.

### 3.11 Browser-Management (`engine/browser.py`)

- Playwright-Singleton (Chromium) mit den Anti-Detection-/Stabilitäts-Flags (`--no-sandbox`, Cache/Throttling deaktiviert, Init-Scripts für `window.getDomPath` und „echter Browser"-Signale).
- **Jeder Job bekommt einen isolierten Kontext** (eigene Cookies/Cache) mit optionalen HTACCESS-Credentials — keine geteilten Sessions zwischen Jobs.

### 3.12 Reports (`app/reports/`)

- Der Generator bekommt das kanonische `ResultsOut`-Modell (`engine/results.py`) + `JobOut` und liefert einen `str`.
- **TXT** ist das einzige Report-Format und gliedert den Bericht (Zusammenfassung, Multi-Resolution-Tests, 404-URLs, Fehler nach Kategorie, detaillierte Fehlerliste).
- Das Schreiben nach `docs/` und das Streamen an den Client übernimmt die API-Schicht (`api/jobs.py`).

## 4. Frontend

### 4.1 Nuxt-SPA

- `ssr: false` — der Nitro-Server liefert das Shell-HTML und proxied `/api/**` per `routeRules` auf `API_URL` (im Compose-Netzwerk `http://api:8000`). Dadurch ist das Frontend immer same-origin, kein CORS im Produktiv-Container.
- **`/ws/**` ist bewusst NICHT als routeRules-Proxy konfiguriert** — der Nitro-HTTP-Proxy kann keine WebSocket-Upgrades. Der WS-Tunnel ist eine eigene Nitro-Server-Route (siehe 3.5).
- `runtimeConfig.apiTarget` liefert das API-Ziel für Server-Routen.

### 4.2 Seiten & Komponenten

- `pages/index.vue` — URL-Formular (`UrlForm.vue`: URL, Suite `bitv`/`wcag`/`all`, max. Seiten, optionale HTACCESS-Zugangsdaten) + `CoverageMap.vue` (Test-Abdeckung aus `GET /api/tests` + `/summary`).
- `pages/jobs/index.vue` — Job-Liste mit Status, Fortschritt, Seiten-/Fehlerzählern; live alle 3 s aktualisiert, solange aktive Jobs laufen; Abbrechen möglich.
- `pages/jobs/[id].vue` — Detailseite:
  - **Live-Bereich** solange der Job läuft: `ProgressPanel.vue` + `StatusLog.vue` (WS-Events); Polling-Fallback alle 2,5 s.
  - **Ergebnis-Bereich** wenn fertig: Umschalter „Nach Test" (`ResultByTest.vue`) vs. „Nach URL" (`ResultByUrl.vue`), Filter, TXT-Export-Button.
  - **Checklisten**: manuelle Tests und Stubs („Noch nicht automatisierte Tests") als aufklappbare Listen.
- `composables/useScan.js` — zentraler API-/WS-Client: `createJob`, `listJobs`, `getJob`, `cancelJob`, `getResults`, `getTests`, `getTestsSummary`, `download` (TXT-Export), `connectWs`. Alle `$fetch`-Aufrufe laufen über `apiFetch`; `connectWs(jobId, { token, … })` hängt das WS-Ticket als `?ws_token=…` an.
- **Auth-Schicht** (`app.vue` + `components/LoginScreen.vue` + `composables/useAuth.js` + `utils/apiFetch.js`):
  - `useAuth` ist ein **Module-Singleton** (`status`: `loading | guest | authed`, `user`); Zustand **nur im Speicher** (kein localStorage). Beim App-Start prüft `init()` über `GET /api/auth/me`, ob eine Bestandssession existiert (httpOnly-Cookie).
  - `app.vue` rendert als **Auth-Gate**: `loading` → leere neutrale Fläche; `guest` → **ausschließlich** `LoginScreen` (kein Header/Footer/Branding/Info); `authed` → bisherige Shell (Header mit Benutzername + „Abmelden“, `NuxtPage`, Footer). `NuxtPage` wird also erst nach erfolgreichem Login gemountet.
  - `LoginScreen.vue` ist bewusst **nackt** (zentriertes Formular auf leerem Grund, generische Fehlermeldung); keine App-Information.
  - `utils/apiFetch.js` (`$fetch.create`) registriert **401-Handler**: Jede abgelaufene Session setzt den Zustand einheitlich auf `guest` zurück → Login-Screen erscheint. (Download via `<a>`-Klick ist browser-level, 401 dort nicht abfangbar — der nächste API-Call flippt zu `guest`.)

### 4.3 Ergebnis-Filter

In `pages/jobs/[id].vue` filtern drei Bedienelemente die Ergebnis-Ansicht:

- **Level-Filter** (`MUSS` / `SOLLTE` / `KANN`),
- **Verantwortung** (technisch / redaktionell),
- **Suchfeld** über `message`, `url`, `test_id`, `dom_path`, `detail`, `resolution`.

Ein `filteredResults`-Computed filtert `by_test` und `by_url` konsistent (nur Tests/URLs mit verbleibenden Findings bleiben sichtbar; `total_findings` wird entsprechend angepasst).

### 4.4 Retest (Backend)

- Retest läuft nur über die API (`POST /api/jobs/retest`) — das Frontend hat keinen Retest-Button mehr. Ein einzelner Befund lässt sich so als Mini-Job ohne Crawl erneut prüfen; der neue Job erscheint in der Job-Liste.
- Retestbar sind Tests aus dem Registry-Snapshot des Laufs, sofern nicht `manual` — Pseudo-Tests wie `LINKS_404` haben keinen Registry-Eintrag und sind nicht retestbar.

## 5. Docker

### 5.1 Services, Ports, Volumes (`docker-compose.yml`)

| Service | Build | Host-Port | Interne Ports/Pfade |
|---|---|---|---|
| `api` | `Dockerfile.api` | `8000:8000` | Uvicorn auf 8000; Swagger `/docs` |
| `web` | `Dockerfile.web` | `3001:3000` | Nitro-Server auf 3000 (Host 3001, da 3000 oft belegt); build-arg `API_URL=http://api:8000` |

Volumes/Bind-Mounts:
- `./data:/app/data` — SQLite (`A11Y_DATABASE_PATH=/app/data/a11y.db`)
- `./docs:/app/docs` — Report-Exporte (`A11Y_OUTPUT_DIR=/app/docs`)

Umgebungen: `PYTHONUNBUFFERED=1`, `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`; `shm_size: "2gb"` (Playwright/Chromium), `restart: unless-stopped`.

### 5.2 Produktions-Override (`docker-compose.prod.yml`)

Basis-Compose + Override zusammen (`docker compose -f docker-compose.yml -f
docker-compose.prod.yml up -d --build`) für den Betrieb **hinter einem
TLS-Reverse-Proxy**:

- `api.ports: !override []` und `web.ports: !override []` — kein öffentlicher
  Host-Port; Clients erreichen die App nur über den Proxy (z. B. Caddy).
  (`!override` ist Compose ≥ v2.24 / v5; ersetzt additiv gemergte Port-Listen.)
- `api`-Environment: `A11Y_SESSION_COOKIE_SECURE=true` (TLS davor) und
  `A11Y_ADMIN_USERNAME`/`A11Y_ADMIN_PASSWORD` aus der Umgebung/`.env` (dort
  chmod 600 — die Datei enthält bewusst keine Werte und keine Server-Topologie).
- Die Anbindung an ein geteiltes Proxy-Netz (damit der Proxy den `web`-Container
  per DNS erreicht) ist server-spezifisch und liegt **nicht** im Repo, sondern in
  der Betriebsdoku des Zielsystems (dort z. B. `compose.vps.yml` + Caddyfile-Route).

### 5.3 Builds

- **`Dockerfile.api`**: Basis `mcr.microsoft.com/playwright/python:v1.48.0-jammy` (Chromium inkl. System-Dependencies unter `/ms-playwright`; `playwright==1.48.0` im pip-Install ist auf die Browser-Revision des Basis-Images gepinnt). Erst Dependencies (`requirements-dev.txt`), dann `COPY backend/ .`. CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`. (bcrypt liefert abi3-Wheels — kein Compiler auf jammy nötig.)
- **`Dockerfile.web`**: Node 22 multi-stage. Build-Stage: `npm ci --no-audit --no-fund --legacy-peer-deps` (Hinweis: `--legacy-peer-deps` wegen einer Peer-Dependency-Kollision von `@bomb.sh/tab` — siehe Kommentar im Dockerfile) + `npm run build`. Runtime-Stage: kopiert nur `.output` + `node_modules`; CMD `node .output/server/index.mjs`.

## 6. Neuen Check hinzufügen (Schritt-für-Schritt)

1. **Kriterium verifizieren** — aus den offiziellen Quellen (W3C/ETSI/BITV) und `docs/bitvtest/*.json`: Nummer, WCAG-Level (A/AA/AAA), BITV-Kategorie (MUSS/SOLLTE/KANN), was genau getestet wird, Ausnahmen. **BITV-Testnummern** stammen aus den 98 Prüfschritten der BITV 2.0 (strukturiert in `docs/bitvtest/*.json`). **Level nicht aus dem Code übernehmen** — gegen die Quellen prüfen.
2. **Typ entscheiden** — `syntax` (statisch via `ctx.soup`/BeautifulSoup), `resolution` (braucht berechnete Styles/Layout → Playwright `ctx.page` pro Auflösung), oder `manual` (Checkliste, kein Algorithmus).
3. **Check-Funktion schreiben** in der eigenen Datei `backend/app/engine/checks/<test_id.lower()>.py` (z. B. `WCAG_1_1_1_IMG_ALT` → `wcag_1_1_1_img_alt.py`). Geteilte Algorithmen (Kontrast, W3C, Label-Erkennung, DOM-Pfad, …) aus `_helpers.py` importieren statt duplizieren:

   ```python
   from ._base import CheckContext, finding, get_dom_path, is_accessible_element

   async def check_xxx(ctx: CheckContext):
       errors = []
       for el in ctx.soup.find_all(...):
           if not is_accessible_element(el):
               continue
           # …Prüfung…
           errors.append(finding("WCAG_X_X_X_KURZNAME", "Meldungstext",
                                 get_dom_path(el), resolution=ctx.resolution))
       return errors
   ```

   Stubs (architektiert, noch ohne Algorithmus): `raise CheckNotImplemented()`.
4. **Registry-Eintrag ergänzen** in `backend/app/engine/registry.py` — alle Felder aus 3.6, insbesondere `module` (= `test_id.lower()`, der Dateiname ohne `.py`), `check` (Funktionsname), `status` (`implemented`/`stub`), `suite` (`bitv`/`wcag`).
5. **Automatische Registrierung prüfen** — `engine/checks/__init__.py` importiert das Modul über `module`+`check`; Auflösungsfehler erscheinen in `MISSING_CHECKS`. Integritätstests laufen lassen:

   ```bash
   docker compose run --rm api pytest tests/test_registry.py -q
   ```

   (`test_no_missing_checks`, `test_every_non_manual_test_has_resolvable_check`, `test_implemented_check_runs_without_crash` u. a.)
6. **Frontend/API** aktualisieren sich automatisch über `GET /api/tests` (Abdeckungs-Map) und `GET /api/jobs/{id}/results` (Checklisten). Manuelle Kriterien erscheinen als „Manuell zu prüfen", Stubs als „Noch nicht automatisierte Tests".
7. **Verifizieren** — Scan gegen eine Testseite bzw. die Integration-Fixture laufen lassen, False-Positives prüfen:

   ```bash
   docker compose run --rm api pytest -m integration
   ```

## 7. Testen (pytest)

- Ausführen im api-Container: `docker compose run --rm api pytest` (mit Live-Mount für lokale Änderungen: `docker compose run --rm -v "G:/Meine Projekte/a11y-scanner/backend:/app" api pytest`).
- **Marker `integration`**: braucht Playwright/Netzwerk (nur im Container sinnvoll, dort sind die Browser installiert): `docker compose run --rm api pytest -m integration`. Der Test startet einen lokalen HTTP-Server gegen `tests/fixtures/site/` und scannt ihn durch den vollen Stack (JobManager → Runner → Crawler → Checks → Persistenz → Ergebnisse).
- Die restlichen Tests laufen als schnelle Unit-Tests mit Fake-Runner (kein echtes Crawling), isolierter Temp-DB und deaktiviertem W3C-Validator (`conftest.py`).
- `pytest.ini_options` in `pyproject.toml`: `asyncio_mode = "auto"` (pytest-asyncio), `testpaths = ["tests"]`, `pythonpath = ["."]`.

## 8. Bekannte Einschränkungen

- **Die App ist kein Source of Truth** für Prüfkriterien — normativ sind die offiziellen Quellen (W3C/ETSI/BITV) und `docs/bitvtest/*.json`. Registry-/Check-Metadaten gegen diese prüfen.
- **W3C-Validator** (`validator.w3.org/nu`, remote API) braucht Netz und kann bei vielen Seiten langsam sein; Umfang via `A11Y_W3C_VALIDATOR_MAX` (0 = aus). In eingeschränkten Umgebungen deaktivieren.
- **Fokus-/Keyboard-Tests** laufen nur bei Viewport-Breite > `keyboard_min_width` (1160 px) — bei 320 px werden sie übersprungen.
- **Manuelle Kriterien** (`type=manual`) werden nicht automatisiert geprüft; sie erscheinen als Checkliste im Ergebnis. **Stubs** sind architektiert, werfen aber `CheckNotImplemented` und werden als „noch nicht implementiert" geführt.
- **Kein Auth**: lokales Single-User-Tool; CORS großzügig, keine Login-Flows.
- **Retest** ist auf einen einzelnen Test + eine URL beschränkt (kein Crawl). Manuelle Kriterien und Pseudo-Tests (`LINKS_404`) sind nicht retestbar.
- **Kein LICENSE** trotz Verweis im README.
- **CI** existiert nicht — die pytest-Suite ist die einzige automatische Absicherung.
