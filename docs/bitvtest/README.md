# BITV-2.0-Prüfschritte — strukturierte Referenz

Die 98 Prüfschritte der BITV 2.0 für den Web-Bereich (inkl. der
EN-301-549-Kapitel 5/6/7/11/12) als eigenständig strukturiertes JSON, je Test
eine Datei. Die Aufbereitung ist **angelehnt an die Vorgaben der BITV 2.0**
und dient als maschinenlesbare Referenz der BITV-Testnummern.

**Referenz für die `bitv`-Felder** in `backend/app/engine/registry.py` — die
Feldwerte müssen gegen diese Dateien verifizierbar sein
(siehe `tests/test_registry.py`).

> **Kein Source of Truth:** Normativ sind ausschließlich die offiziellen
> Quellen (W3C/ETSI/BITV 2.0). Diese Dateien sind ein Arbeitsabbild der
> Prüfkriterien und können Fehler enthalten.

## Dateien

```
docs/bitvtest/
├── _index.json       # Index über alle Tests (slug, status, datei, titel, wcag22)
├── 5.2.json          # EN-301-549-Kapitel 5.2 (Aktivierung von Barrierefreiheitsfunktionen)
├── 6.1.json          # Kapitel 6 (Zwei-Wege-Sprachkommunikation)
├── 7.1.1.json        # Kapitel 7 (Video-Untertitel/Audiodeskription)
├── 9.1.1.1b.json     # Kapitel 9 (WCAG-basierte Prüfschritte)
├── 11.7.json         # Kapitel 11.7 (Benutzerdefinierte Einstellungen)
└── 12.2.4.json       # Kapitel 12 (Dokumentation/Support)
```

## Schema je Test-Datei

```json
{
  "bitv_nummer": "9.1.4.3",
  "titel": "Kontraste von Texten ausreichend",
  "wcag22": {                       // null, wenn keine WCAG-Einordnung vorliegt
    "wcag_version": "2.2",          // "2.2" oder "2.1" (eine Seite nutzt WCAG 2.1)
    "guideline": "Guideline 1.4 Distinguishable: …",
    "success_criterion": "1.4.3 Contrast (Minimum)",
    "level": "AA",
    "techniken": {                  // Kategorien (General/HTML/ARIA/Failures)
      "General": ["G18: …", "…"]
    }
  },
  "abschnitte": [
    {
      "id": "was_wird_geprueft",    // "_was_wird_geprueft" → ohne führendes "_"
      "titel": "Was wird geprüft?",
      "untersektionen": [            // ODER flaches "inhalt_markdown"
        {"titel": "1. Anwendbarkeit", "inhalt_markdown": "…"}
      ]
    }
  ]
}
```

Typische `abschnitte`-IDs: `was_wird_geprueft`, `warum_wird_das_geprueft`,
`wie_wird_geprueft`, `einordnung_des_pruefschritts`, `quellen`,
`fragen_zu_diesem_pruefschritt`. Jeder Block hat entweder `untersektionen`
(intern h3+-Überschriften, ideal für „Wie wird geprüft: 1. Anwendbarkeit /
2. Prüfung / 3. Hinweise") oder flaches `inhalt_markdown`.

## Nutzung

- **Frontend-Texte:** `titel` + `abschnitte[].untersektionen` liefern
  beschreibenden Text pro BITV-Test (z. B. für eine Kriterien-Detailansicht).
- **Fehlende Checks entwickeln:** `wie_wird_geprueft` beschreibt die konkrete
  Prüfanleitung — direkt als `test_hint`/Algorithmus-Grundlage verwendbar.
- **Bestehende Checks prüfen:** `wcag22` mappt BITV↔WCAG (Kriterium + Level);
  damit lässt sich die Registry-Abdeckung gegen die 98 Prüfschritte abgleichen.
- **Level:** `wcag22.level` ist das WCAG-Level der Zuordnung. Hinweis: 57 von
  98 Prüfschritten haben eine WCAG-Einordnung; die Kapitel 5/6/7/11/12 sowie
  drei 9.x-Prüfschritte (9.1.1.1d, 9.1.2.1, 9.2.4.3) haben keine.

## Regenerieren

Die App bindet die JSONs über das Generierungsskript ein (erzeugt
`backend/app/engine/bitv_steps.py` mit 98 Einträgen sowie Stub-Checks).
Das Skript nutzt nur die Standardbibliothek — Aufruf ohne Container:

```bash
python backend/scripts/generate_bitv_steps.py --write
```
