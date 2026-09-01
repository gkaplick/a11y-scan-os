<script setup>
/**
 * Test-Abdeckungs-Map (task #15).
 *
 * Lädt die Registry über GET /api/tests + /api/tests/summary und zeigt, welche
 * Prüfkriterien die App automatisiert abdeckt und welche manuell geprüft
 * werden müssen (es gibt keine Stub-Kategorie mehr).
 * Aktualisiert sich automatisch, weil es ausschließlich aus der Registry des
 * Backends abgeleitet wird (eine Aktualisieren-Schaltfläche lädt neu).
 *
 * Gruppierung (Nutzer-Entscheid): Die Haupttabelle stapelt drei Abschnitte
 * BITV → WCAG → EN untereinander. Ein Kriterium gehört zu genau einer Gruppe
 * über das `category`-Feld (BITV | WCAG | EN 301 549). Die drei Systeme sind
 * vollständig getrennt — jedes Kriterium hat genau eine Nummer (`id`), keine
 * Querweise, keine Duplikate.
 */
const { getTests } = useScan()
const { isDisabled, isCategoryDisabled, setTest, setCategory, clearAll, seedDefaults: seedDisabledDefaults } = useDisabledTests()
const { assessments, getAssessment, setAssessment, seedDefaults: seedAssessmentDefaults } = useManualAssessments()

const tests = ref([])
const loading = ref(true)
const error = ref('')

const search = ref('')
const statusFilter = ref('all')
const normFilter = ref('all')

// Status ist binär: entweder automatisiert (implementierter Check) oder
// manuell zu prüfen (keine Stub-Kategorie mehr — die App ist vorige Stubs
// automatisch zu manuellen Kriterien erklärt worden).
const STATUS_META = {
  implemented: { color: 'success', label: 'Automatisiert' },
  manual: { color: 'neutral', label: 'Manuell' },
}

// MUSS/SOLLTE/KANN — die normative Verbindlichkeit eines Kriteriums.
const LEVEL_META = {
  MUSS: { color: 'error', label: 'Muss' },
  SOLLTE: { color: 'warning', label: 'Sollte' },
  KANN: { color: 'neutral', label: 'Kann' },
}

// Norm-Gruppen in der Reihenfolge des Nutzers: erst BITV, dann WCAG, dann EN.
// Die Gruppierung läuft über das `category`-Feld der Registry (disjunkt).
const NORM_ORDER = ['BITV', 'WCAG', 'EN 301 549']

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    tests.value = await getTests()
    // Default-Deaktivierung seeden (einmalig je Seed-Version): manuelle
    // BITV-Kapitel (6/7/11/12) + EN-Kapitel 6/7/11/12 (Telefonie, Video-
    // kommunikation, Software, Dokumentation — für reine Webprojekte meist
    // nicht anwendbar). Dazu die Dropdown-Defaults (nicht_anwendbar) für die
    // manuellen BITV-Kapitel. Die Kapitel bleiben dabei aufgeklappt (keine
    // Kategorie-Keys) — nur die Zeilen sind ausgegraut, Schalter und
    // Dropdowns bleiben erreichbar.
    seedDisabledDefaults([...manualDefaultOffTestIds.value, ...enDefaultOffTestIds.value])
    seedAssessmentDefaults(manualTestIds.value)
  } catch (e) {
    error.value = e?.data?.detail || 'Abdeckung konnte nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

const normOptions = [
  { value: 'all', label: 'Alle Normen' },
  ...NORM_ORDER.map((n) => ({ value: n, label: n })),
]

const matchesFilter = (t) => {
  if (statusFilter.value !== 'all' && t.status !== statusFilter.value) return false
  const term = search.value.trim().toLowerCase()
  if (!term) return true
  const hay = [t.test_id, t.id, t.title]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return hay.includes(term)
}

// Aussagekräftige Kapitel-Überschriften je Norm: Die BITV/EN-Kapitel folgen
// der EN-301-549-Gliederung, die WCAG-Kapitel sind die vier Prinzipien.
// Die gesetzlichen BITV-Anforderungen (§3–§7, nicht aus EN 301 549) bilden
// eine eigene Gruppe.
const CHAPTER_LABELS = {
  BITV: {
    '§': 'Gesetzliche Anforderungen (BITV 2.0)',
    5: 'Allgemeine Anforderungen',
    6: 'Zwei-Wege-Sprachkommunikation',
    7: 'Kommunikationstechnik mit Videofunktionen',
    9: 'Web',
    11: 'Software',
    12: 'Dokumentation und Unterstützungsdienste',
  },
  WCAG: {
    1: 'Wahrnehmbar',
    2: 'Bedienbar',
    3: 'Verständlich',
    4: 'Robust',
  },
  'EN 301 549': {
    5: 'Allgemeine Anforderungen',
    6: 'Zwei-Wege-Sprachkommunikation',
    7: 'Kommunikationstechnik mit Videofunktionen',
    11: 'Software',
    12: 'Dokumentation und Unterstützungsdienste',
  },
}

// Kapitel (Major) eines Tests. Ableitung aus der test_id, nicht aus der `id`:
// Die `id` der EN-AAA-Kriterien (z. B. "1.4.8") trägt die WCAG-Nummer, nicht
// die EN-Kapitel-Nummer. Alle §-Anforderungen fallen in eine gemeinsame Gruppe.
const majorOf = (t) => {
  const id = (t.id || '').trim()
  if (id.startsWith('§')) return '§'
  const m = (t.test_id || '').match(/^(?:BITV|WCAG|EN)_(\d+)/)
  return m ? m[1] : 'Sonstige'
}

const majorRank = (major) => {
  if (major === '§') return -1 // gesetzliche Anforderungen stehen am Anfang
  const n = Number(major)
  return Number.isNaN(n) ? 999 : n
}

const majorLabel = (norm, major) =>
  CHAPTER_LABELS[norm]?.[major] ??
  (major === 'Sonstige' ? 'Weitere' : `Kapitel ${major}`)

// --- Toggle „nicht relevante Tests" ---
// Deaktivierte Tests werden beim Scan übersprungen und nicht bewertet.
// Kategorie-/Kapitel-Toggles wirken auf die VOLLSTÄNDIGE Testliste (nicht auf
// die gefilterte Ansicht) — Filter betreffen nur die Anzeige.
const testsOfNorm = (norm) => tests.value.filter((t) => t.category === norm)
const testsOfGroup = (norm, major) =>
  testsOfNorm(norm).filter((t) => majorOf(t) === major)

// --- Schlüssel für Kategorie-Toggles (Abschnitt/Kapitel) ---
const sectionKey = (norm) => `section:${norm}`
const groupKey = (norm, major) => `group:${norm}:${major}`

// --- Manuell zu bewertende Kriterien ---
// Es gibt keine Stubs mehr — jedes Kriterium ist entweder automatisiert oder
// manuell (Status "manual"). Statt des Status-Badges erscheint für manuelle
// Kriterien ein Dropdown (Erfüllt / Nicht Erfüllt / Nicht Anwendbar, Default
// "Nicht Anwendbar"), dessen Wert in den Report fließt.
const isManualTest = (t) => t.status === 'manual'

const manualTestIds = computed(() =>
  tests.value.filter(isManualTest).map((t) => t.test_id),
)

// BITV-Kapitel 6/7/11/12 (Zwei-Wege-Sprachkommunikation, Videofunktionen,
// Software, Dokumentation & Unterstützungsdienste) sind per Default deaktiviert:
// Telefonie-/Video-/Software-/Doku-Anforderungen sind für reine Webprojekte
// meist nicht anwendbar. Diese Tests sind per Default deaktiviert
// (seedDefaults) und ihr Dropdown-Wert fließt nur in den Report, wenn der
// Nutzer sie auf relevant stellt — deaktiviert zählen sie als "nicht_relevant"
// und sind nicht Teil des Reports. Andere manuelle Kriterien bleiben aktiv.
const MANUAL_DEFAULT_OFF_CHAPTERS = new Set(['6', '7', '11', '12'])
const manualDefaultOffTestIds = computed(() =>
  tests.value
    .filter((t) => isManualTest(t) && MANUAL_DEFAULT_OFF_CHAPTERS.has(majorOf(t)))
    .map((t) => t.test_id),
)

// EN-Kapitel 6/7/11/12 (Zwei-Wege-Sprachkommunikation, Kommunikationstechnik
// mit Videofunktionen, Software, Dokumentation und Unterstützungsdienste)
// sind per Default deaktiviert: Der Fokus der App sind Webprojekte (EN-Kapitel
// 9 = WCAG). Telefonie-/Software-/Doku-Anforderungen aktiviert der Nutzer bei
// Bedarf per Kapitel-Toggle.
const EN_DEFAULT_OFF_CHAPTERS = new Set(['6', '7', '11', '12'])
const enDefaultOffTestIds = computed(() =>
  tests.value
    .filter((t) => t.category === 'EN 301 549' && EN_DEFAULT_OFF_CHAPTERS.has(majorOf(t)))
    .map((t) => t.test_id),
)

const ASSESSMENT_ITEMS = [
  { value: 'erfuellt', label: 'Erfüllt' },
  { value: 'nicht_erfuellt', label: 'Nicht Erfüllt' },
  { value: 'nicht_anwendbar', label: 'Nicht Anwendbar' },
]

// --- EN 301 549: Querverweis auf die zugrunde liegenden BITV-/WCAG-Tests ---
// EN-Kriterien, deren Ergebnis aus WCAG-/BITV-Tests geerbt wird (en_sources
// aus der Registry), zeigen die Quell-Tests als Badges anstelle des
// Status-Badges, z. B. "BITV 9.1.3.2" oder "WCAG 1.3.2".
const testsById = computed(() => new Map(tests.value.map((t) => [t.test_id, t])))
const srcBadge = (sid) => {
  const t = testsById.value.get(sid)
  if (!t) return sid
  const prefix = t.category === 'BITV' ? 'BITV' : t.category === 'WCAG' ? 'WCAG' : t.category
  return `${prefix} ${t.id || sid}`
}
const hasEnSources = (t) => t.category === 'EN 301 549' && t.en_sources?.length > 0

// --- Kategorie-Toggles (Abschnitt/Kapitel) ---
// Der Eltern-Schalter zeigt NUR den expliziten Kategorie-Zustand
// (isCategoryDisabled) — nicht, ob einzelne Unter-Tests zufällig deaktiviert
// sind. Das Zuklappen (Akkordeon) gilt ebenso nur für ganze Kategorien:
// Einzeltests werden beim Deaktivieren weiterhin nur ausgegraut, nie versteckt.
const toggleSection = (section, on) => {
  const ts = testsOfNorm(section.norm).map((t) => t.test_id)
  const groupKeys = [
    ...new Set(testsOfNorm(section.norm).map((t) => groupKey(section.norm, majorOf(t)))),
  ]
  setCategory(section.key, ts, on)
  for (const gk of groupKeys) setCategory(gk, [], on)
}

const toggleGroup = (norm, major, on) => {
  const ts = testsOfGroup(norm, major).map((t) => t.test_id)
  setCategory(groupKey(norm, major), ts, on)
  // Kapitel wieder aktiviert → Sektion nicht mehr als Ganzes deaktiviert, also
  // den Abschnitts-Key löschen, damit die Zeilen wieder sichtbar werden.
  if (on) setCategory(sectionKey(norm), [], true)
}

// Der Seed beim Erstbesuch deaktiviert nur die Tests selbst (test_ids) — die
// Kategorie-Keys bleiben unberührt, damit die manuellen Kapitel aufgeklappt
// und ihre Einzeltest-Schalter sichtbar bleiben (Akkordeon nur bei explizitem
// Kategorie-Toggle).

const totalDisabled = computed(() =>
  tests.value.filter((t) => isDisabled(t.test_id)).length,
)

// Übersicht oben = nur der aktuell aktive Stand (was im nächsten Scan wirklich
// geprüft wird): deaktivierte (ausgeklappte) Tests sind herausgerechnet.
// Jedes Kriterium ist entweder automatisiert oder manuell (keine Stubs mehr).
const activeTests = computed(() => tests.value.filter((t) => !isDisabled(t.test_id)))
const overview = computed(() => {
  const ts = activeTests.value
  return {
    total: ts.length,
    implemented: ts.filter((t) => t.status === 'implemented').length,
    manual: ts.filter((t) => t.status === 'manual').length,
  }
})

const normState = computed(() => {
  const out = {}
  for (const norm of NORM_ORDER) {
    const ts = testsOfNorm(norm)
    out[norm] = {
      total: ts.length,
      disabledCount: ts.filter((t) => isDisabled(t.test_id)).length,
    }
  }
  return out
})

// Info-Modal: Klick auf das Fragezeichen-Icon öffnet die vollständige
// Kriterien-Info (Was/Wie wird geprüft + Lösung) als Modal (TestInfoModal).
const infoTest = ref(null)

// Drei Abschnitte (BITV → WCAG → EN); innerhalb einer Kategorie werden die
// Tests mit Zwischen-Headlines nach ihrer Major-Nummer (Kapitel) gruppiert.
const sections = computed(() =>
  NORM_ORDER
    .filter((norm) => normFilter.value === 'all' || normFilter.value === norm)
    .map((norm) => {
      const entries = tests.value.filter((t) => t.category === norm)
      const filtered = entries.filter(matchesFilter)
      const byMajor = new Map()
      for (const t of filtered) {
        const major = majorOf(t)
        if (!byMajor.has(major)) byMajor.set(major, [])
        byMajor.get(major).push(t)
      }
      const groups = [...byMajor.entries()]
        .map(([major, groupEntries]) => ({
          major,
          label: majorLabel(norm, major),
          count: groupEntries.length,
          entries: groupEntries,
          key: groupKey(norm, major),
          // Deaktiviert-Zähler über die VOLLSTÄNDIGE Gruppe (unabhängig vom Filter)
          disabledCount: testsOfGroup(norm, major).filter((t) => isDisabled(t.test_id)).length,
        }))
        .sort((a, b) => majorRank(a.major) - majorRank(b.major))
      return {
        norm,
        label: norm,
        key: sectionKey(norm),
        total: entries.length,
        count: filtered.length,
        groups,
      }
    })
    .filter((s) => s.count > 0)
)

// Überblick pro Norm-Gruppe — NUR über die aktiven Tests (deaktivierte/
// ausgeklappte sind herausgerechnet). Jedes Kriterium ist entweder
// automatisiert oder manuell (keine Stubs mehr).
const normRows = computed(() =>
  NORM_ORDER.map((norm) => {
    const entries = activeTests.value.filter((t) => t.category === norm)
    return {
      norm,
      label: norm,
      total: entries.length,
      implemented: entries.filter((t) => t.status === 'implemented').length,
      manual: entries.filter((t) => t.status === 'manual').length,
    }
  })
)
</script>

<template>
  <div>
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <h2 class="text-xl font-semibold">Test-Abdeckung</h2>
    </div>

    <UAlert v-if="error" color="error" :title="error" icon="i-lucide-circle-alert" class="mb-4" />

    <div v-if="tests.length" class="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
      <div class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
        <div class="text-2xl font-bold">{{ overview.total }}</div>
        <div class="text-sm text-neutral-500">Kriterien aktiv</div>
      </div>
      <div class="rounded-lg border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900 dark:bg-emerald-950">
        <div class="text-2xl font-bold text-emerald-700 dark:text-emerald-400">
          {{ overview.implemented }}
        </div>
        <div class="text-sm text-emerald-700 dark:text-emerald-400">Automatisiert abgedeckt</div>
      </div>
      <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 dark:border-neutral-800 dark:bg-neutral-900">
        <div class="text-2xl font-bold">{{ overview.manual }}</div>
        <div class="text-sm text-neutral-500">Manuell zu prüfen</div>
      </div>
    </div>

    <div v-if="normRows.length" class="mb-6 overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
      <table class="w-full text-sm">
        <thead class="bg-neutral-100 text-left dark:bg-neutral-800">
          <tr>
            <th class="px-3 py-2 font-medium">Kategorie</th>
            <th class="px-3 py-2 text-center font-medium">Gesamt</th>
            <th class="px-3 py-2 text-center font-medium">Automatisiert</th>
            <th class="px-3 py-2 text-center font-medium">Manuell</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in normRows"
            :key="row.norm"
            class="border-t border-neutral-200 dark:border-neutral-800"
          >
            <td class="px-3 py-2 font-medium">{{ row.label }}</td>
            <td class="px-3 py-2 text-center">{{ row.total }}</td>
            <td class="px-3 py-2 text-center">
              <span v-if="row.implemented" class="font-semibold text-emerald-600 dark:text-emerald-400">{{ row.implemented }}</span>
              <span v-else class="text-neutral-400">0</span>
            </td>
            <td class="px-3 py-2 text-center">
              <span v-if="row.manual" class="text-neutral-500">{{ row.manual }}</span>
              <span v-else class="text-neutral-400">0</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p class="px-3 py-2 text-xs text-neutral-400">
        Die drei Systeme sind vollständig getrennt — jedes Kriterium hat genau eine Kategorie und eine Nummer (keine Querweise).
      </p>
    </div>

    <div class="mb-3 flex flex-wrap gap-3">
      <UInput v-model="search" placeholder="Test-ID, Nummer oder Titel filtern…" class="max-w-xs" icon="i-lucide-search" />
      <USelect
        v-model="statusFilter"
        :items="[
          { value: 'all', label: 'Alle Status' },
          { value: 'implemented', label: 'Automatisiert' },
          { value: 'manual', label: 'Manuell' },
        ]"
        class="w-44"
      />
      <USelect v-model="normFilter" :items="normOptions" class="w-44" />
    </div>

    <div
      v-if="totalDisabled"
      class="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 dark:border-sky-900 dark:bg-sky-950/40"
    >
      <span class="text-sm text-sky-700 dark:text-sky-300">
        Als nicht relevant deaktiviert: {{ totalDisabled }} Kriterien — werden beim nächsten Scan übersprungen und nicht bewertet.
      </span>
      <UButton size="xs" color="neutral" variant="soft" :title="'Alle ' + totalDisabled + ' Kriterien wieder aktivieren'" @click="clearAll">
        Alle aktivieren
      </UButton>
    </div>

    <div v-if="tests.length" class="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
      <table class="w-full text-sm">
        <thead class="bg-neutral-100 text-left dark:bg-neutral-800">
          <tr>
            <th class="px-3 py-2 font-medium">Nummer</th>
            <th class="px-3 py-2 font-medium">Titel</th>
            <th class="px-3 py-2 font-medium">Level</th>
            <th class="px-3 py-2 font-medium">Status</th>
            <th class="px-3 py-2 text-center font-medium">Relevant</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="section in sections" :key="section.norm">
            <tr class="border-t border-neutral-200 bg-neutral-100 dark:border-neutral-800 dark:bg-neutral-800/50">
              <th colspan="4" class="px-3 py-2 text-left font-medium">
                <span class="inline-flex items-center gap-1.5">
                  <span>{{ section.label }} — {{ section.count }} Kriterien</span>
                  <span v-if="normState[section.norm].disabledCount" class="ml-1 text-xs font-normal text-neutral-500">
                    ({{ normState[section.norm].disabledCount }} deaktiviert)
                  </span>
                </span>
              </th>
              <th class="px-3 py-2 text-center">
                <USwitch
                  :model-value="!isCategoryDisabled(section.key)"
                  size="sm"
                  :aria-label="'Gesamte Kategorie ' + section.label + ' als nicht relevant deaktivieren'"
                  @update:model-value="(on) => toggleSection(section, on)"
                />
              </th>
            </tr>
            <template v-if="!isCategoryDisabled(section.key)">
              <template v-for="group in section.groups" :key="section.norm + ':kapitel:' + group.major">
                <tr class="border-t border-neutral-200 bg-neutral-50 dark:border-neutral-800 dark:bg-neutral-900">
                  <th
                    colspan="4"
                    class="px-3 py-1.5 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400"
                  >
                    <span class="inline-flex items-center gap-1">
                      <span>{{ group.label }} — {{ group.count }} Kriterien</span>
                      <span v-if="group.disabledCount" class="ml-1 normal-case text-neutral-400">
                        ({{ group.disabledCount }} deaktiviert)
                      </span>
                    </span>
                  </th>
                  <th class="px-3 py-1.5 text-center">
                    <USwitch
                      :model-value="!isCategoryDisabled(group.key)"
                      size="sm"
                      :aria-label="'Kapitel ' + group.label + ' als nicht relevant deaktivieren'"
                      @update:model-value="(on) => toggleGroup(section.norm, group.major, on)"
                    />
                  </th>
                </tr>
                <template v-if="!isCategoryDisabled(group.key)">
                  <tr
                    v-for="t in group.entries"
                    :key="section.norm + ':' + t.test_id"
                    class="border-t border-neutral-200 dark:border-neutral-800"
                    :class="{ 'opacity-50': isDisabled(t.test_id) }"
                  >
                    <td class="px-3 py-1.5 whitespace-nowrap font-mono text-xs">
                      <span v-if="t.id">{{ t.id }}</span>
                      <span v-else class="text-neutral-400">—</span>
                    </td>
                    <td class="px-3 py-1.5">
                      <span class="inline-flex items-center gap-1">
                        <span>{{ t.title }}</span>
                        <UButton
                          icon="i-lucide-circle-help"
                          color="neutral"
                          variant="ghost"
                          size="xs"
                          class="-my-0.5"
                          :aria-label="'Info zu ' + t.title"
                          @click="infoTest = t"
                        />
                      </span>
                    </td>
                    <td class="px-3 py-1.5 whitespace-nowrap">
                      <UBadge
                        v-if="t.level"
                        :color="LEVEL_META[t.level]?.color || 'neutral'"
                        variant="soft"
                        size="sm"
                      >
                        {{ LEVEL_META[t.level]?.label || t.level }}
                      </UBadge>
                      <span v-else class="text-neutral-400">—</span>
                    </td>
                    <td class="px-3 py-1.5">
                      <UBadge
                        v-if="isDisabled(t.test_id)"
                        color="neutral"
                        variant="soft"
                        size="sm"
                      >
                        Nicht relevant
                      </UBadge>
                      <USelect
                        v-else-if="isManualTest(t)"
                        :model-value="getAssessment(t.test_id)"
                        :items="ASSESSMENT_ITEMS"
                        size="xs"
                        class="w-40"
                        :aria-label="'Bewertung für ' + t.title"
                        @update:model-value="(v) => setAssessment(t.test_id, v)"
                      />
                      <span v-else-if="hasEnSources(t)" class="inline-flex flex-wrap gap-1">
                        <UBadge
                          v-for="sid in t.en_sources"
                          :key="sid"
                          color="info"
                          variant="soft"
                          size="sm"
                        >
                          {{ srcBadge(sid) }}
                        </UBadge>
                      </span>
                      <UBadge v-else :color="STATUS_META[t.status]?.color || 'neutral'" variant="soft" size="sm">
                        {{ STATUS_META[t.status]?.label || t.status }}
                      </UBadge>
                    </td>
                    <td class="px-3 py-1.5 text-center">
                      <USwitch
                        :model-value="!isDisabled(t.test_id)"
                        size="sm"
                        :aria-label="'Test ' + t.title + ' als nicht relevant deaktivieren'"
                        @update:model-value="(on) => setTest(t.test_id, on)"
                      />
                    </td>
                  </tr>
                </template>
              </template>
            </template>
          </template>
          <tr v-if="!sections.length">
            <td colspan="5" class="px-3 py-4 text-center text-neutral-500">Keine Treffer für diesen Filter.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-else-if="loading" class="py-4 text-sm text-neutral-500">Abdeckung wird geladen…</p>

    <!-- Info-Modal: vollständige Kriterien-Info -->
    <TestInfoModal v-if="infoTest" :test="infoTest" @close="infoTest = null" />
  </div>
</template>
