/**
 * Manuelle Bewertung nicht automatisierbarer Kriterien (BITV-Abschnitte 6/7
 * und 11/12: Zwei-Wege-Sprachkommunikation, Kommunikationstechnik mit Video-
 * funktionen, Software, Dokumentation & Unterstützungsdienste).
 *
 * Diese Kriterien sind nicht automatisierbar (Status manual). Statt
 * sie als "nicht automatisiert" zu verbuchen, bewertet der Nutzer sie per
 * Dropdown: "Erfüllt" | "Nicht Erfüllt" | "Nicht Anwendbar" — Default
 * "Nicht Anwendbar" (zählt in der System-Bewertung als bestanden, siehe
 * results.py). Der Zustand lebt im Browser (localStorage) und wird beim
 * Scan als `manual_assessments` (test_id → Wert) ans Backend geschickt.
 *
 * Der Zustand ist ein Modul-Singleton (ref) → CoverageMap und Scan-Formular
 * sehen immer denselben Stand.
 */
import { ref } from 'vue'

const KEY = 'a11y_manual_assessments'
const DEFAULT = 'nicht_anwendbar'

/** Gültige Werte — dieselben wie im Backend (schemas/runner/results). */
export const MANUAL_VALUES = ['erfuellt', 'nicht_erfuellt', 'nicht_anwendbar']

const load = () => {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || '{}')
    return raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : {}
  } catch {
    return {}
  }
}

const assessments = ref(load())

const persist = () => {
  try {
    localStorage.setItem(KEY, JSON.stringify(assessments.value))
  } catch {
    /* localStorage nicht verfügbar (privates Fenster) → nur in-memory */
  }
}

export const useManualAssessments = () => {
  /** Aktuelle Bewertung eines Tests (Default "nicht_anwendbar"). */
  const getAssessment = (testId) => assessments.value[testId] || DEFAULT

  const setAssessment = (testId, value) => {
    if (!MANUAL_VALUES.includes(value)) return
    assessments.value = { ...assessments.value, [testId]: value }
    persist()
  }

  /**
   * Fehlende Defaults (nicht_anwendbar) für die übergebenen test_ids ergänzen.
   * Überschreibt KEINE bereits getroffene Bewertung — dient nur dazu, dass der
   * Default überhaupt im Scan ankommt (der Backend-Default ist "nicht
   * bewertet", nicht "nicht anwendbar").
   */
  const seedDefaults = (testIds) => {
    let changed = false
    const next = { ...assessments.value }
    for (const id of testIds) {
      if (!next[id]) {
        next[id] = DEFAULT
        changed = true
      }
    }
    if (changed) {
      assessments.value = next
      persist()
    }
  }

  return {
    /** Reaktive Map test_id → "erfuellt"|"nicht_erfuellt"|"nicht_anwendbar". */
    assessments,
    getAssessment,
    setAssessment,
    seedDefaults,
  }
}
