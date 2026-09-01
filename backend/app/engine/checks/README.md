# engine/checks — eine Datei pro Test

Hier liegen die **Check-Implementierungen** des Scanners — die eigentlichen Tests
zu den Registry-Kriterien in `backend/app/engine/registry.py`.

## Namenskonvention

**Eine Datei pro Test-ID** (`module`-Feld der Registry = `test_id.lower()`), das
Präfix kennzeichnet die Normengruppe:

| Präfix | Gruppe                | Beispiel                                              |
|--------|-----------------------|-------------------------------------------------------|
| `wcag_`| WCAG 2.1              | `wcag_1_1_1_img_alt.py` (→ `WCAG_1_1_1_IMG_ALT`)     |
| `en_`  | EN 301 549            | `en_7_2_1_ad_playback.py` (→ `EN_7_2_1_AD_PLAYBACK`) |
| `bitv_`| BITV 2.0 (reine BITV) | `bitv_7_declaration.py` (→ `BITV_7_DECLARATION`)     |

BITV- und WCAG-Tests haben **unterschiedliche Testkriterien** und teilen sich
keine Struktur — die Trennung ist die Datei- und Präfix-Ebene. Der Test
`test_module_field_equals_test_id_lower` in `backend/tests/test_registry.py`
sichert die Konvention dauerhaft ab.

## Dateien

- `_base.py` — Kontrakt: `CheckContext`, `Finding`, `finding()`,
  `get_dom_path()`, `is_accessible_element()`, `CheckNotImplemented`.
- `_helpers.py` — **geteilte Primitiven** (Farb-/Kontrast-Kern, W3C-Lauf,
  Label-/Namen-Erkennung, DOM-Pfad, Medien-Selektion, …). Kriterien-parametrisiert
  und normen-neutral: Sie kennen keine Test-ID, sondern bekommen die Kriterien
  als Parameter.
- `__init__.py` — Dispatch: importiert aus jedem Registry-Eintrag
  (`module` + `check`) die Check-Funktion und baut `CHECK_FUNCTIONS`.
  Auflösungsfehler landen in `MISSING_CHECKS`.

## Regel

- Eine Check-Datei importiert **nur** aus `_base.py` und `_helpers.py` —
  **keine Cross-Imports zwischen Check-Dateien**. Ein BITV-/EN-Test ruft nie eine
  WCAG-Testdatei auf (und umgekehrt).
- Geteilte Logik gehört nach `_helpers.py`, nicht in eine andere Testdatei.
- Stubs (`status="stub"`) werfen `CheckNotImplemented` und erscheinen als
  „noch nicht implementiert".

Ausführlich dokumentiert in `docs/ARCHITEKTUR.md` (Abschnitt „Neuen Check
hinzufügen") und `CLAUDE.md` (Konventionen).
