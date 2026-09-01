<script setup>
useHead({ title: 'Scan — A11Y Scanner by G.Kaplick' })
const route = useRoute()
const jobId = route.params.id
const { getJob, getResults, cancelJob, download } = useScan()

const job = ref(null)
const results = ref(null)
const events = ref([])
const view = ref('test') // 'test' | 'url'
const error = ref('')
const cancelling = ref(false)

// Filter (Ergebnis-Ansicht). Die „Alle“-Einträge nutzen das Sentinel 'alle'
// statt einer leeren Zeichenkette: reka-ui/Nuxt UI v3 wirft bei SelectItems
// mit leerem value einen Fehler („must have a value prop that is not an empty
// string“). Im Filter wird 'alle' auf „kein Filter“ normalisiert.
const levelFilter = ref('alle')
const responsibilityFilter = ref('alle')
const normFilter = ref('alle')
const search = ref('')

// Endgerät-Filter (Multiselect): 320 (mobil) / 1920 (desktop) /
// auflösungsunabhängig (Befunde ohne Auflösung, z. B. Syntax-Checks).
const deviceFilter = ref([])
const DEVICE_OPTIONS = [
  { value: '320', label: '320 px (mobil)' },
  { value: '1920', label: '1920 px (desktop)' },
  { value: 'none', label: 'Auflösungsunabhängig' },
]
const deviceKeyOf = (f) =>
  f.resolution == null || f.resolution === '' ? 'none' : String(f.resolution)

const matchesSearch = (f) => {
  const q = search.value.trim().toLowerCase()
  if (!q) return true
  return [f.message, f.url, f.test_id, f.dom_path, f.detail, f.resolution]
    .filter(Boolean).join(' ').toLowerCase().includes(q)
}

/** Gefilterte Sicht auf die Ergebnisse (by_test/by_url), Rest unverändert. */
const filteredResults = computed(() => {
  const r = results.value
  if (!r) return null
  const level = levelFilter.value === 'alle' ? '' : levelFilter.value
  const isWcagLevel = level === 'A' || level === 'AA' || level === 'AAA'
  // Level-Auswahl: BITV-Level (MUSS/SOLLTE/KANN) gegen `level`, WCAG-Level
  // (A/AA/AAA) gegen `wcag_level`.
  const matchLevel = (item) => !level || (isWcagLevel ? item.wcag_level === level : item.level === level)
  const resp = responsibilityFilter.value === 'alle' ? '' : responsibilityFilter.value
  const norm = normFilter.value === 'alle' ? '' : normFilter.value
  const devices = deviceFilter.value
  const devOk = (f) => !devices.length || devices.includes(deviceKeyOf(f))
  const byTest = r.by_test
    .filter((t) =>
      matchLevel(t)
      && (!resp || t.responsibility === resp)
      && (!norm || t.category === norm),
    )
    .map((t) => ({ ...t, findings: t.findings.filter((f) => matchesSearch(f) && (!norm || f.category === norm) && devOk(f)) }))
    .filter((t) => t.findings.length > 0)
  const noFilter = !level && !resp && !norm && !search.value.trim() && !devices.length
  const byUrl = r.by_url
    .map((u) => ({
      ...u,
      findings: u.findings.filter((f) =>
        matchesSearch(f) && matchLevel(f) && (!resp || f.responsibility === resp) && (!norm || f.category === norm) && devOk(f)),
    }))
    .filter((u) => u.findings.length > 0 || noFilter)
  // Bestandene Kriterien (keine Befunde) für die grüne „Bestanden"-Sektion.
  // Filter wirken wie auf by_test (Level, Verantwortung, Norm); Suche und
  // Endgerät betreffen nur Befunde.
  const passed = (r.tests || []).filter((t) =>
    t.result === 'bestanden'
    && matchLevel(t)
    && (!resp || t.responsibility === resp)
    && (!norm || t.category === norm),
  )
  const filteredTotal = byTest.reduce((n, t) => n + t.findings.length, 0)
  return { ...r, by_test: byTest, by_url: byUrl, total_findings: filteredTotal, passed }
})

const finished = computed(() => job.value && ['done', 'failed', 'canceled'].includes(job.value.status))

// Manuelle Bewertungen (aus dem Scan-Snapshot, Werte des Backends)
const ASSESSMENT_META = {
  erfuellt: { color: 'success', label: 'Erfüllt' },
  nicht_erfuellt: { color: 'error', label: 'Nicht Erfüllt' },
  nicht_anwendbar: { color: 'neutral', label: 'Nicht Anwendbar' },
}

// EN 301 549: Quell-Referenzen der geerbten BITV/WCAG-Tests anzeigen
const testsById = computed(() =>
  new Map((results.value?.tests || []).map((t) => [t.test_id, t])),
)
const enSourceLabel = (sid) => {
  const src = testsById.value.get(sid)
  const prefix = src?.category === 'BITV' ? 'BITV' : src?.category === 'WCAG' ? 'WCAG' : ''
  return `${prefix} ${src?.id || sid}`.trim()
}

// --- EN 301 549: Ergebnis je Kriterium (Endbericht nach Test) ---
// Das EN-System umfasst die EN-Kriterien (Kapitel 5–12) PLUS die WCAG-Tests
// als EN-Kapitel 9 (EN verweist für Web vollständig auf WCAG 2.1).
const EN_CHAPTER_LABELS = {
  5: 'Allgemeine Anforderungen',
  6: 'Zwei-Wege-Sprachkommunikation',
  7: 'Kommunikationstechnik mit Videofunktionen',
  9: 'Web (WCAG 2.1)',
  11: 'Software',
  12: 'Dokumentation und Unterstützungsdienste',
}
const enChapter = (t) => {
  if (t.category === 'EN 301 549') return (t.test_id || '').match(/^EN_(\d+)/)?.[1] || null
  if (t.category === 'WCAG') return '9'
  return null
}
const enChapters = computed(() => {
  // Vom Nutzer deaktivierte Kriterien (Status nicht_relevant) gehören nicht ins
  // Testergebnis — sie wurden vom Scan ausgeschlossen und nur die aktiven
  // Kriterien bilden den EN-Endbericht.
  const ts = (results.value?.tests || []).filter((t) => enChapter(t) && t.status !== 'nicht_relevant')
  const byChapter = new Map()
  for (const t of ts) {
    const ch = enChapter(t)
    if (!byChapter.has(ch)) byChapter.set(ch, [])
    byChapter.get(ch).push(t)
  }
  return [...byChapter.entries()]
    .sort((a, b) => Number(a[0]) - Number(b[0]))
    .map(([ch, tests]) => ({ ch, label: EN_CHAPTER_LABELS[ch] || `Kapitel ${ch}`, tests }))
})
const EN_RESULT_META = {
  bestanden: { color: 'success', label: 'Bestanden' },
  nicht_bestanden: { color: 'error', label: 'Nicht bestanden' },
  nicht_anwendbar: { color: 'neutral', label: 'Nicht anwendbar' },
  nicht_bewertet: { color: 'neutral', label: 'Nicht bewertet' },
}
const enKindBadge = (kind) =>
  kind === 'erweitert'
    ? { color: 'warning', label: 'Erweitert (AAA)' }
    : { color: 'info', label: 'Verbindlich' }

let ws = null
let timer = null

// --- Sitzungs-Dauer (wie lange der Scan läuft / gelaufen ist) ---
// `now` tickt sekündlich, solange der Job nicht fertig ist; die Dauer wird aus
// created_at/started_at → finished_at/jetzt abgeleitet.
const now = ref(Date.now())
let clockTimer = null
const startClock = () => {
  stopClock()
  clockTimer = setInterval(() => { now.value = Date.now() }, 1000)
}
const stopClock = () => {
  if (clockTimer) { clearInterval(clockTimer); clockTimer = null }
}
const formatDuration = (ms) => {
  const total = Math.max(0, Math.floor(ms / 1000))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const pad = (n) => String(n).padStart(2, '0')
  return (h > 0 ? `${h}:` : '') + `${pad(m)}:${pad(s)}`
}
const durationLabel = computed(() => {
  const j = job.value
  if (!j) return ''
  const startRaw = j.started_at || j.created_at
  if (!startRaw) return ''
  const end = j.finished_at ? new Date(j.finished_at).getTime() : now.value
  const ms = end - new Date(startRaw).getTime()
  const d = formatDuration(ms)
  if (j.status === 'queued') return `Wartet: ${d}`
  if (j.status === 'running') return `Läuft seit ${d}`
  return `Dauer: ${d}`
})

const STATUS_COLOR = {
  queued: 'neutral',
  running: 'primary',
  done: 'success',
  failed: 'error',
  canceled: 'neutral',
}
const STATUS_TEXT = {
  queued: 'Wartend',
  running: 'Läuft',
  done: 'Fertig',
  failed: 'Fehlgeschlagen',
  canceled: 'Abgebrochen',
}

const loadResults = async () => {
  try {
    results.value = await getResults(jobId)
  } catch (e) {
    error.value = e?.data?.detail || 'Ergebnisse konnten nicht geladen werden.'
  }
}

const stopLive = () => {
  stopClock()
  if (timer) { clearInterval(timer); timer = null }
  if (ws) { try { ws.close() } catch { /* ignorieren */ } ws = null }
}

const refreshJob = async () => {
  try {
    job.value = await getJob(jobId)
    if (finished.value) {
      stopLive()
      await loadResults()
    }
  } catch (e) {
    error.value = e?.data?.detail || 'Job konnte nicht geladen werden.'
  }
}

onMounted(async () => {
  await refreshJob()
  if (!finished.value) {
    startClock()
    const { connectWs } = useScan()
    ws = connectWs(jobId, {
      onEvent: (ev) => {
        events.value.push(ev)
        if (events.value.length > 300) events.value.splice(0, events.value.length - 300)
        if (ev.type === 'done') job.value = { ...job.value, status: 'done', progress: 100 }
        if (ev.type === 'error') job.value = { ...job.value, status: 'failed' }
      },
      onClose: () => {
        if (!finished.value) refreshJob()
      },
    })
    timer = setInterval(refreshJob, 2500)
  }
})

onUnmounted(stopLive)

const cancel = async () => {
  if (cancelling.value) return
  cancelling.value = true
  try {
    await cancelJob(jobId)
    await refreshJob()
  } catch (e) {
    // 409 = Job ist gerade erst fertig/fehlgeschlagen geworden — das ist kein
    // Fehler, sondern ein normaler Wettlauf (Button war beim Klick noch da).
    if (e?.status === 409) {
      await refreshJob()
    } else {
      error.value = e?.data?.detail || 'Abbrechen fehlgeschlagen.'
    }
  } finally {
    cancelling.value = false
  }
}

const SUITE_LABELS = { bitv: 'BITV 2.0', wcag: 'WCAG 2.1', all: 'BITV 2.0 + WCAG 2.1' }
const suiteLabel = (s) => SUITE_LABELS[s] || s
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <NuxtLink to="/jobs" class="text-sm text-primary-500 underline">← Alle Scans</NuxtLink>
        <h1 v-if="job" class="mt-1 flex items-center gap-2 break-all font-mono text-lg font-semibold">
          {{ job.url }}
          <UBadge :color="STATUS_COLOR[job.status]" variant="soft">{{ STATUS_TEXT[job.status] || job.status }}</UBadge>
          <span v-if="durationLabel" class="text-xs font-normal text-neutral-500">{{ durationLabel }}</span>
        </h1>
        <p v-if="job" class="mt-1 text-sm text-neutral-500">
          Suite: {{ suiteLabel(job.suite) }} · {{ job.page_count }} Seiten · {{ job.finding_count }} Fehler
        </p>
      </div>
      <div class="flex gap-2">
        <UButton
          v-if="job && (job.status === 'queued' || job.status === 'running')"
          color="error"
          variant="soft"
          icon="i-lucide-square"
          :loading="cancelling"
          @click="cancel"
        >
          Abbrechen
        </UButton>
        <UButton
          v-if="finished && results"
          color="neutral"
          variant="soft"
          icon="i-lucide-file-text"
          @click="download(jobId)"
        >
          TXT
        </UButton>
      </div>
    </div>

    <UAlert v-if="error" color="error" :title="error" icon="i-lucide-circle-alert" />
    <UAlert v-if="job?.status === 'failed'" color="error" :title="job.error || 'Scan fehlgeschlagen'" icon="i-lucide-circle-alert" />

    <!-- Live-Bereich -->
    <template v-if="job && !finished">
      <div class="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
        <ProgressPanel :job="job" />
      </div>
      <StatusLog :events="events" />
    </template>

    <!-- Ergebnis -->
    <template v-if="finished && results">
      <SystemSummary :systems="results.system_bewertung" />
      <div class="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
        <div class="mb-4 flex flex-wrap items-center gap-2">
          <UButton
            :color="view === 'test' ? 'primary' : 'neutral'"
            :variant="view === 'test' ? 'solid' : 'soft'"
            icon="i-lucide-list-checks"
            @click="view = 'test'"
          >
            Nach Test
          </UButton>
          <UButton
            :color="view === 'url' ? 'primary' : 'neutral'"
            :variant="view === 'url' ? 'solid' : 'soft'"
            icon="i-lucide-globe"
            @click="view = 'url'"
          >
            Nach URL
          </UButton>

          <span class="mx-1 h-5 w-px bg-neutral-200 dark:bg-neutral-700" />

          <USelect
            v-model="normFilter"
            :items="[
              { value: 'alle', label: 'Norm: alle' },
              { value: 'BITV', label: 'BITV' },
              { value: 'WCAG', label: 'WCAG' },
              { value: 'EN 301 549', label: 'EN 301 549' },
            ]"
            size="sm"
            class="w-40"
          />
          <USelect
            v-model="levelFilter"
            :items="[
              { value: 'alle', label: 'Alle Level' },
              { value: 'MUSS', label: 'MUSS' },
              { value: 'SOLLTE', label: 'SOLLTE' },
              { value: 'KANN', label: 'KANN' },
              { value: 'A', label: 'A (WCAG)' },
              { value: 'AA', label: 'AA (WCAG)' },
              { value: 'AAA', label: 'AAA (WCAG)' },
            ]"
            size="sm"
            class="w-36"
          />
          <USelect
            v-model="responsibilityFilter"
            :items="[
              { value: 'alle', label: 'Verantwortung: alle' },
              { value: 'technisch', label: 'Technisch' },
              { value: 'redaktionell', label: 'Redaktionell' },
            ]"
            size="sm"
            class="w-44"
          />
          <USelectMenu
            v-model="deviceFilter"
            :items="DEVICE_OPTIONS"
            multiple
            value-key="value"
            placeholder="Endgerät: alle"
            size="sm"
            class="w-56"
          />
          <UInput
            v-model="search"
            size="sm"
            icon="i-lucide-search"
            placeholder="Suchen (URL, Test, Pfad)…"
            class="w-60"
          />
          <span class="ml-auto text-sm text-neutral-500">
            {{ filteredResults.total_findings }} Fehler auf {{ results.page_count }} Seiten
          </span>
        </div>

        <ResultByTest
          v-if="view === 'test'"
          :results="filteredResults"
        />
        <ResultByUrl
          v-else
          :results="filteredResults"
        />
      </div>

      <!-- EN 301 549: Endbericht nach Test, nach Kapitel gegliedert -->
      <details
        class="rounded-2xl border border-neutral-200 bg-white shadow-sm dark:border-neutral-800 dark:bg-neutral-900"
      >
        <summary class="cursor-pointer select-none px-5 py-4 font-medium">
          EN 301 549 — Ergebnis je Kriterium ({{ enChapters.reduce((n, c) => n + c.tests.length, 0) }})
          <span class="ml-2 text-xs font-normal text-neutral-500">
            Verbindlich = WCAG A/AA + EN-Kapitel 5–12 · Erweitert (AAA) = informatorisch
          </span>
        </summary>
        <div class="max-h-[28rem] space-y-4 overflow-y-auto border-t border-neutral-200 px-5 py-4 dark:border-neutral-800">
          <section v-for="ch in enChapters" :key="ch.ch">
            <h3 class="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
              Kapitel {{ ch.ch }} — {{ ch.label }}
            </h3>
            <ul class="space-y-1">
              <li v-for="t in ch.tests" :key="t.test_id" class="flex flex-wrap items-center gap-2 text-sm">
                <UBadge
                  :color="EN_RESULT_META[t.result]?.color || 'neutral'"
                  variant="soft"
                  size="xs"
                >
                  {{ EN_RESULT_META[t.result]?.label || t.result }}
                </UBadge>
                <UBadge
                  v-if="t.en_kind"
                  :color="enKindBadge(t.en_kind).color"
                  variant="outline"
                  size="xs"
                >
                  {{ enKindBadge(t.en_kind).label }}
                </UBadge>
                <span class="font-mono text-xs text-neutral-400">{{ t.id }}</span>
                <span>{{ t.title }}</span>
              </li>
            </ul>
          </section>
        </div>
      </details>

      <!-- Manuell zu prüfende Kriterien (Checkliste) -->
      <details class="rounded-2xl border border-neutral-200 bg-white shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
        <summary class="cursor-pointer select-none px-5 py-4 font-medium">
          Manuell zu prüfen ({{ results.manual_tests.length }})
        </summary>
        <ul v-if="results.manual_tests.length" class="max-h-80 space-y-1 overflow-y-auto border-t border-neutral-200 px-5 py-3 dark:border-neutral-800">
          <li v-for="t in results.manual_tests" :key="t.test_id" class="text-sm">
            <span class="font-mono text-xs text-neutral-400">{{ t.id }}</span>
            <span class="ml-2">{{ t.title }}</span>
            <UBadge
              v-if="ASSESSMENT_META[t.assessment]"
              :color="ASSESSMENT_META[t.assessment].color"
              variant="soft"
              size="xs"
              class="ml-2"
            >
              {{ ASSESSMENT_META[t.assessment].label }}
            </UBadge>
          </li>
        </ul>
        <p v-else class="border-t border-neutral-200 px-5 py-3 text-sm text-neutral-500 dark:border-neutral-800">
          Keine manuellen Kriterien in dieser Suite.
        </p>
      </details>
    </template>

    <div v-if="!job" class="py-12 text-center text-neutral-500">Lade Scan…</div>
  </div>
</template>
