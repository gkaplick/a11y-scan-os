# A11y-Scanner — Barrierefreiheit automatisiert prüfen

Automatisierter Website-Scanner, der Webangebote gegen **WCAG 2.1** (A/AA/AAA),
**BITV 2.0** und **EN 301 549** prüft. Docker-First-Webapp aus FastAPI-Backend
und Nuxt-4-SPA-Frontend — ohne Installation auf dem Host.

Der Scanner crawlt eine Website (BFS, domänen-beschränkt), rendert sie bei
**320 px und 1920 px** und prüft jede Seite per Playwright + DOM-Analyse.
Ergebnisse siehst du live im Browser (WebSocket) und kannst sie als
Text-Report (TXT) exportieren.

## ✨ Features

- **Drei Prüfsysteme in einem Scan** — getrenntes Urteil je System
  (BITV binär, EN 301 549 binär, WCAG mit erzieltem Konformitätsniveau A/AA/AAA).
- **Vollständige BITV-2.0-Pflicht** (`suite "bitv"`, 208 Tests: die 98
  strukturierten BITV-Prüfschritte plus die zugrunde liegenden
  WCAG-A/AA-Kriterien) · optionale **WCAG-Suite** (`suite "wcag"`, 28 Tests) ·
  beides zusammen (`suite "all"`, 236 Tests).
- **Zwei Auflösungen** — jede Seite wird bei 320 px (Mobile) und 1920 px
  (Desktop) geprüft; Fokus- und Keyboard-Tests ab 1160 px.
- **Crawl mit Domänen-Scoping** — BFS über interne Links, 404-Erkennung,
  Respekt vor `robots.txt`-irrelevanten Ausschluss-Pfaden.
- **Live-Fortschritt** — WebSocket-Events für Status, aktuelle URL und
  gefundene Befunde, ohne Neuladen.
- **Befund-Screenshots** — visueller Nachweis je Befund direkt im Ergebnis.
- **TXT-Report** — herunterladbar und zusätzlich als Datei in `docs/`.
- **Zugangsgeschützte Bereiche** — HTACCESS-Zugangsdaten pro Job (nie als
  Default im Code).

## 🚀 Schnellstart

Voraussetzung: [Docker](https://www.docker.com/) (Desktop oder Engine).

```bash
# Start → Web http://localhost:3001, API http://localhost:8000 (Swagger: /docs)
docker compose up -d

# Logs des Backends verfolgen
docker compose logs -f api
```

Danach http://localhost:3001 öffnen, eine URL eintragen und scanen.

Nach Änderungen neu bauen: `docker compose up --build`.

## 🧭 So nutzt du den Scanner

1. **URL eintragen** — beliebige Website; der Scanner crawlt die Domain BFS.
2. **Suite scannen** — standardmäßig die volle Suite (`all`): BITV-2.0- und
   WCAG-Kriterien; **EN 301 549** wird automatisch mitbewertet. Einzelne
   Kriterien blendest du in der Test-Tabelle aus.
3. **Scan starten** — Fortschritt läuft live im Browser.
4. **Ergebnisse auswerten** — nach Test oder nach URL gruppiert, mit
   Konformitäts-Niveau, Schweregrad, Fundstellen und Screenshot.
5. **Befunde verstehen** — jeder Befund trägt Test-ID, Kriterium,
   Beschreibung, Lösungshinweis und den echten DOM-Pfad der Fundstelle.
6. **Exportieren** — TXT-Report herunterladen; die Datei liegt zusätzlich
   unter `docs/Barrierefreiheit_Report_<domain>_<timestamp>.txt`.

## 🧪 Demo- und Test-Website

Das Repo enthält eine generierte Test-Website mit **Positiv-/Negativ-Paaren**
zu jedem automatisiert prüfbaren Kriterium (Konformität vs. Verstoß):

```bash
# 1) Test-Website generieren (einmalig, nach Änderungen an testwebsite/generate.py)
docker compose run --rm api python testwebsite/generate.py

# 2) Servieren → http://localhost:8099
docker compose up -d testwebsite
```

In der App unter `http://localhost:8099` Suite **„Alle“** wählen — die
Positiv-Seiten müssen befundfrei sein, die Negativ-Seiten genau die
gelisteten `test_id`s feuern. Details in `testwebsite/README.md`.

## 🏗️ Architektur (Kurzfassung)

```
backend/                    # FastAPI + Playwright (Python ≥ 3.11, async)
├── app/
│   ├── main.py             # FastAPI-App, Lifespan (DB-Schema, Browser-Warmstart)
│   ├── config.py           # pydantic-settings, Env-Overrides A11Y_*
│   ├── db.py / models.py   # SQLite/SQLAlchemy: Job, Page, Finding, TestRecord
│   ├── api/                # jobs.py (REST), tests.py (Registry), ws.py (Live-Progress)
│   ├── engine/
│   │   ├── registry.py     # Test-Registry (maschinelles Abbild des Katalogs)
│   │   ├── checks/         # eine Datei pro Test-ID (_base.py, _helpers.py, …)
│   │   ├── runner.py       # Scan-Runner (Crawl + Dispatch)
│   │   ├── crawler.py      # BFS-Queue, Domänen-Scoping, 404-Cache
│   │   ├── browser.py      # Playwright-Singleton + isolierte Kontexte
│   │   ├── job_manager.py  # Job-Lebenszyklus + Semaphore
│   │   ├── progress.py     # ProgressBroker für WebSocket-Events
│   │   └── results.py      # Ergebnis-Aggregation (by_test / by_url)
│   └── reports/            # txt_report.py
├── tests/                  # pytest-Suite (Unit + Integration; Fixtures in tests/fixtures/site/)
frontend/                   # Nuxt 4 SPA (ssr: false), Nuxt UI v3, Port 3001
├── app/                    # pages/, components/, composables/useScan.js
└── server/routes/ws/jobs/[id].ts   # crossws-WebSocket-Tunnel zum Backend
testwebsite/                # Generator der Test-Fixture (site/ + catalog.json)
docs/                       # bitvtest-Katalog + ARCHITEKTUR.md (Report-Exporte lokal)
```

Ausführliche Doku der Module und Abläufe: **`docs/ARCHITEKTUR.md`**.

## 🧩 Test-Registry und Suiten

Die `REGISTRY` in `backend/app/engine/registry.py` ist die zentrale Liste
aller Kriterien — je Eintrag `test_id`, `suite`, `level` (MUSS/SOLLTE/KANN),
`wcag_level` (A/AA/AAA), `category` (BITV/WCAG/EN 301 549), `type`
(`syntax`|`resolution`|`manual`), `module` + `check`, `status`
(`implemented`|`stub`|`manual`) sowie `description`/`solution`/`test_hint`.

- **`bitv`** (Default) — BITV-2.0-Pflichtumfang, 208 Tests: die 98
  strukturierten BITV-Prüfschritte plus die zugrunde liegenden
  WCAG-A/AA-Kriterien.
- **`wcag`** — WCAG-Suite, 28 Tests: optionale WCAG-Kriterien (AAA) über die
  gesetzliche Pflicht hinaus.
- **`all`** — beide Suiten zusammen, 236 Tests.

Die Bewertung läuft quer durch die Suiten in drei gleichrangigen Systemen
(BITV · WCAG · EN 301 549): Jedes Kriterium trägt genau eine Kategorie und
eine Nummer; EN 301 549 erbt die Ergebnisse der BITV-/WCAG-Kriterien
(WCAG-AAA zählt dort informatorisch als „erweitert").

Der `type` eines Checks bestimmt den Prüfweg:

| Typ | Prüfung |
| --- | --- |
| `syntax` | statisch 1× pro Seite (BeautifulSoup, `ctx.soup`) |
| `resolution` | Playwright pro Auflösung (`ctx.page` + `ctx.resolution`) |
| `manual` | Checkliste, nicht automatisierbar |

Nur `status == "implemented"` zählt in der Ergebnis-Bewertung; Stubs und
manuelle Kriterien werden als „nicht automatisiert" ausgewiesen, aber nicht
als bestanden gewertet. Der `status` wird beim Import automatisch aus dem
Check-Quelltext abgeleitet — neue Checks brauchen kein Status-Update.

## ⚙️ Konfiguration

pydantic-settings, Umgebungsvariablen mit Präfix `A11Y_`:

| Variable | Bedeutung |
| --- | --- |
| `A11Y_DEBUG` | Debug-Modus |
| `A11Y_MAX_PAGES_PER_PROJECT` | Seitenlimit pro Scan (0 = unbegrenzt) |
| `A11Y_W3C_VALIDATOR_MAX` | W3C-Validator: 0=aus, -1=alle, N=erste N Seiten |
| `A11Y_DATABASE_PATH` | Pfad der SQLite-DB |
| `A11Y_OUTPUT_DIR` | Ausgabe-Verzeichnis für Reports |
| `A11Y_MAX_PARALLEL_JOBS` | parallele Scans (Default 3) |
| `A11Y_DEFAULT_SUITE` | Standard-Suite |
| `A11Y_KEYBOARD_MIN_WIDTH` | Mindestbreite für Fokus-/Keyboard-Tests (1160 px) |
| `A11Y_TEST_RESOLUTIONS` | Test-Auflösungen (Default 320px, 1920px) |

**Zugangsdaten** (HTACCESS) kommen pro Job aus dem Formular bzw. der Umgebung —
die `config.py` enthält keine Default-Credentials, es werden keine Secrets
committet.

## 🧑‍💻 Neuen Check anlegen

Ausführlich in `docs/ARCHITEKTUR.md`. Kurzfassung:

1. **Kriterium verifizieren** — gegen die offiziellen Quellen (W3C/ETSI/BITV)
   und `docs/bitvtest/*.json`, inkl. **Level**.
2. **Check-Funktion** in eigener Datei
   `backend/app/engine/checks/<test_id.lower()>.py` schreiben
   (`async def check_xxx(ctx: CheckContext) -> list[Finding]`); geteilte
   Algorithmen aus `_helpers.py` importieren. Stub-Checks werfen
   `CheckNotImplemented`.
3. **Registry-Eintrag** ergänzen (`module` = `test_id.lower()`, `check`-Name) —
   die Registrierung erfolgt automatisch über `engine/checks/__init__.py`.
4. **Integritätstests** laufen lassen:
   `docker compose run --rm api pytest tests/test_registry.py -q`.

**Duplikate vermeiden:** genau eine Datei pro Test-ID; geteilte Logik gehört
nach `_helpers.py`.

## 🧪 Entwicklung und Tests

Dev-Mode mit Hot Reload (Code wird live gemountet, kein Rebuild):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
#   api: uvicorn --reload (backend/app live) · web: Nuxt-Dev-Server mit HMR
#   → gleiche URL http://localhost:3001
```

Frontend-Dev ohne Docker: `cd frontend && npm run dev` → http://localhost:3001.

Tests und Lint im API-Container:

```bash
# Unit-Tests (ohne Integration)
docker compose run --rm api pytest -q

# Integrationstest (echter Playwright-Scan der Test-Website)
docker compose run --rm api pytest tests/test_testwebsite.py -m integration

# Einzelne Datei
docker compose run --rm api pytest tests/test_registry.py -q

# Lint (flake8, E501 ignoriert)
docker compose run --rm api flake8 app tests
```

## ⚠️ Bekannte Grenzen

- Der W3C-Validator (`validator.w3.org/nu`, Remote-API) braucht Netz; in
  eingeschränkten Umgebungen `A11Y_W3C_VALIDATOR_MAX=0`.
- Lokales Single-User-Tool ohne Authentifizierung — nicht als öffentlicher
  Multi-User-Dienst gedacht.
- Export-Dateien in `docs/` (Reporte) liegen außerhalb der Datenbank und
  werden beim Löschen eines Scans nicht mitentfernt.

## 📄 Lizenz

Noch **keine Lizenzdatei** ausgewählt. Bis zur Entscheidung gilt: Alle
Rechte vorbehalten. Wenn du das Projekt weiterverwenden möchtest, sprich den
Autor an.
