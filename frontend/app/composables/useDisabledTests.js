/**
 * Globale Auswahl „nicht relevanter" Tests (Toggle in der großen Test-Tabelle).
 *
 * Der Zustand lebt im Browser (localStorage) und wird beim nächsten Scan als
 * `disabled_test_ids` an das Backend geschickt — dort werden die Tests weder
 * ausgeführt noch bewertet (Status "nicht_relevant").
 *
 * Zwei Ebenen, bewusst getrennt (Nutzer-Vorgabe):
 * - **test_ids** (flach): die tatsächlich deaktivierten Tests.
 * - **Kategorie-Keys** (`a11y_disabled_categories`): welche Abschnitts-/Kapitel-
 *   Toggles der Nutzer EXPLIZIT ausgeschaltet hat (z. B. `section:BITV`,
 *   `group:BITV:9`). Der Eltern-Schalter zeigt NUR diesen expliziten Zustand —
 *   nicht, ob einzelne Unter-Tests zufällig deaktiviert sind. Nur weil ein
 *   Sub-Test in "Web" deaktiviert wird, wird also nicht der "Web"-Schalter
 *   ausgegraut (das wäre irreführend, der Scan überspringt ja nur den einen
 *   Test). Umgekehrt setzt ein Kategorie-Toggle seine gesamte Untermenge.
 *
 * Der Zustand ist ein Modul-Singleton (ref) → Toggles auf der Übersicht und
 * das Scan-Formular sehen immer denselben Stand, ohne Event-Geflacker.
 */
import { ref } from 'vue'

const KEY = 'a11y_disabled_test_ids'
const KEY_CATEGORIES = 'a11y_disabled_categories'
// Einmalige Default-Deaktivierung: Wird bei jeder Änderung der Defaults
// (z. B. EN-Kapitel 6/7/11/12 neu dabei) um +1 erhöht, damit auch Browser mit
// bereits existierendem Seed den neuen Stand erhalten.
const KEY_VERSION = 'a11y_disabled_seed_version'
const SEED_VERSION = '2'

const loadTests = () => {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(raw) ? new Set(raw) : new Set()
  } catch {
    return new Set()
  }
}

const loadCategories = () => {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY_CATEGORIES) || '[]')
    return Array.isArray(raw) ? new Set(raw) : new Set()
  } catch {
    return new Set()
  }
}

const disabled = ref(loadTests())
const categories = ref(loadCategories())

const persist = () => {
  try {
    localStorage.setItem(KEY, JSON.stringify([...disabled.value]))
    localStorage.setItem(KEY_CATEGORIES, JSON.stringify([...categories.value]))
  } catch {
    /* localStorage nicht verfügbar (privates Fenster) → nur in-memory */
  }
}

export const useDisabledTests = () => {
  const isDisabled = (testId) => disabled.value.has(testId)

  /** Einzelnen Test an/aus schalten (on = true → Test ist wieder aktiv). */
  const setTest = (testId, on) => {
    if (on) disabled.value.delete(testId)
    else disabled.value.add(testId)
    // Ein einzelner Test-Toggle berührt KEINE Kategorie-Keys: Der Eltern-
    // Schalter zeigt nur den expliziten Kategorie-Zustand (siehe Kopf).
    persist()
  }

  /**
   * Kategorie an/aus schalten (Abschnitt oder Kapitel). `key` ist der
   * explizite Kategorie-Zustand (z. B. "section:BITV"), `testIds` die Menge
   * der zugehörigen Tests. Der Key wird nur hier gesetzt/gelöscht — nie durch
   * einzelne Test-Toggles.
   */
  const setCategory = (key, testIds, on) => {
    if (on) {
      categories.value.delete(key)
      for (const tid of testIds) disabled.value.delete(tid)
    } else {
      categories.value.add(key)
      for (const tid of testIds) disabled.value.add(tid)
    }
    persist()
  }

  /** Expliziter Kategorie-Zustand (false = Kategorie wurde nicht ausgeschaltet). */
  const isCategoryDisabled = (key) => categories.value.has(key)

  const clearAll = () => {
    disabled.value = new Set()
    categories.value = new Set()
    persist()
  }

  /**
   * Default-Deaktivierung der übergebenen Tests — einmalig je Seed-Version
   * (beim allerersten Aufruf ODER sobald SEED_VERSION hochgezogen wurde, wenn
   * sich die Defaults ändern). Die bestehende Auswahl des Nutzers bleibt
   * erhalten: Es werden nur Defaults ergänzt, nie etwas entfernt.
   * Dient dazu, dass manuell zu prüfende Tests (BITV 6/7/11/12) sowie die
   * EN-Kapitel 6/7/11/12 per Default deaktiviert sind — der Nutzer aktiviert
   * sie bei Bedarf einzeln oder per Kapitel-Toggle.
   *
   * Wichtig: Der Seed setzt KEINE Kategorie-Keys — die manuellen Kapitel
   * bleiben also aufgeklappt (Zeilen ausgegraut, Einzeltest-Schalter und
   * Dropdowns erreichbar). Das Akkordeon klappt eine Kategorie nur zu, wenn
   * der Nutzer sie selbst explizit per Kapitel-/Abschnitt-Schalter deaktiviert.
   */
  const seedDefaults = (testIds) => {
    if (localStorage.getItem(KEY_VERSION) === SEED_VERSION) return
    for (const tid of testIds) disabled.value.add(tid)
    persist()
    localStorage.setItem(KEY_VERSION, SEED_VERSION)
  }

  return {
    /** Reaktives Set der deaktivierten test_ids (Modul-Singleton). */
    disabled,
    /** Reaktives Set der explizit ausgeschalteten Kategorie-Keys. */
    categories,
    isDisabled,
    isCategoryDisabled,
    setTest,
    setCategory,
    clearAll,
    seedDefaults,
  }
}
