# A11Y Test-Website

Demo- **und** Test-Website für den WCAG/BITV/EN Barrierefreiheits-Scanner: zu
jedem automatisiert prüfbaren Kriterium gibt es zwei Seiten —

| Seite | Erwartung |
|---|---|
| `<slug>-positiv.html` | **konform** — soll **keine** Befunde für die gelisteten test_ids erzeugen |
| `<slug>-negativ.html` | **Verstoß** — soll genau die gelisteten test_ids feuern |

Die 54 Kriterien decken **alle 76 implementierten Checks** ab (verifiziert
durch den test_ids-Abgleich in `site/catalog.json`). Die drei Testsysteme
(WCAG / BITV / EN) sind getrennte Seiten; wo WCAG und BITV **unterschiedlich**
urteilen (z. B. generischer Linktext: WCAG-Verstoß, BITV mit Kontext-Ausnahme),
gibt es je eine eigene Seite — die Seite beschriftet nur die test_ids, die auf
ihr wirklich feuern.

## Nutzung

```bash
# 1) Website generieren (einmalig, nach Änderungen an generate.py)
docker compose run --rm api python testwebsite/generate.py

# 2) Servieren (nginx, Port 8099)
docker compose up -d testwebsite
# → http://localhost:8099
```

In der App unter `http://localhost:8099` **Suite „Alle“** wählen — die
Positiv-/Negativ-Paare umfassen auch die optionalen WCAG-AAA-Zusatzkriterien
(`wcag`), die in der Default-Suite `bitv` nicht laufen.

## Katalog & Wahrheitsquelle

- `generate.py` enthält den `CATALOG` (Metadaten + HTML-Beispiele je Kriterium)
  und baut `site/` mit gemeinsamem, selbst konformem Chrome (Header, Nav,
  test_ids-Badges, Partner-/Index-Links, Footer).
- `site/catalog.json` wird beim Build geschrieben und ist die **Wahrheitsquelle
  für den pytest** — auch im Container, wo nur `site/` liegt
  (Dockerfile.api: `COPY testwebsite/site /app/testwebsite`), nicht der
  Generator selbst.
- `site/` ist vollständig generiert; Änderungen gehören in `generate.py`.

## Tests (Integration)

```bash
# Im Container (Browser vorhanden), nach docker compose build api:
docker compose run --rm api pytest -m integration tests/test_testwebsite.py -q
```

Der Test macht **einen** Gesamt-Scan (`suite="all"`, ~5–10 Min) und asserted je
Kriterium: Negativ-Seite feuert ihre test_ids, Positiv-Seite bleibt frei von
ihnen. Fehlschläge nennen die Kriterien-Seiten einzeln.

## Ausnahme: `html-syntax` (W3C-Validator)

Das Kriterium `html-syntax` (WCAG 4.1.1 / BITV 9.4.1.1) ist **nicht** Teil der
pytest-Absicherung (`pytest: False` im Katalog): Seine Checks laufen über den
externen W3C-Validator (`validator.w3.org/nu`), der in Tests deaktiviert
(`A11Y_W3C_VALIDATOR_MAX=0`) und netzabhängig ist. Im Live-Scan bei
eingeschränktem Netz gilt dasselbe (`A11Y_W3C_VALIDATOR_MAX=0`).
