<script setup>
/**
 * Ergebnis-Perspektive 1: nach Test → betroffene URLs.
 *
 * Die Tests werden nach Dringlichkeit gruppiert: MUSS → SOLLTE → KANN
 * (normatives Level der Registry). Innerhalb eines Levels stehen die Tests
 * mit den meisten Befunden zuerst. Tests ohne Level (z. B. Pseudo-Test
 * LINKS_404) bilden den Auffang-Block „Weitere" am Ende. Bestandene
 * Kriterien (ohne Befunde) stehen grün in einer eigenen Sektion.
 */
const props = defineProps({
  results: { type: Object, required: true },
})

const LEVEL_ORDER = ['MUSS', 'SOLLTE', 'KANN']
const levelRank = (level) => {
  const i = LEVEL_ORDER.indexOf(level)
  return i === -1 ? LEVEL_ORDER.length : i
}
const levelColor = (level) => ({ MUSS: 'error', SOLLTE: 'warning', KANN: 'neutral' })[level] || 'neutral'
const levelDesc = (level) => ({
  MUSS: 'Muss erfüllt sein',
  SOLLTE: 'Sollte erfüllt sein',
  KANN: 'Kann erfüllt sein',
  Weitere: 'Ohne normatives Level',
})[level] || level

const grouped = computed(() => {
  const byLevel = new Map()
  for (const t of props.results.by_test) {
    const key = LEVEL_ORDER.includes(t.level) ? t.level : 'Weitere'
    if (!byLevel.has(key)) byLevel.set(key, [])
    byLevel.get(key).push(t)
  }
  return [...byLevel.entries()]
    .map(([level, entries]) => {
      const tests = [...entries].sort(
        (a, b) => b.count - a.count || a.title.localeCompare(b.title, 'de'),
      )
      return {
        level,
        count: tests.reduce((n, t) => n + t.findings.length, 0),
        tests,
      }
    })
    .sort((a, b) => levelRank(a.level) - levelRank(b.level))
})

const levelText = (level) => level || '—'
const stdLabel = (f) => {
  if (!f.category) return ''
  return f.number ? `${f.category} ${f.number}` : f.category
}

// Bestandene Kriterien (grüne Sektion) — liefert filteredResults aus
// results.tests (Status „bestanden" = implementiert ohne Befund).
const passed = computed(() => props.results.passed || [])

// Info-Modal: Die Fehler-Zeilen (by_test) tragen nur Befund-Metadaten — die
// vollen Kriterien-Infos (description/solution/test_hint) kommen aus dem
// TestOut-Snapshot in props.results.tests.
const testsById = computed(() => new Map((props.results.tests || []).map((t) => [t.test_id, t])))
const infoOf = (item) => ({ ...item, ...(testsById.value.get(item.test_id) || {}) })
const infoTest = ref(null)
</script>

<template>
  <div class="space-y-3">
    <template v-if="results.by_test.length">
      <template v-for="g in grouped" :key="g.level">
        <div
          class="flex flex-wrap items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-100 px-4 py-2 dark:border-neutral-800 dark:bg-neutral-800/50"
        >
          <UBadge :color="levelColor(g.level)" variant="soft">{{ g.level }}</UBadge>
          <span class="text-sm font-medium">{{ levelDesc(g.level) }}</span>
          <span class="ml-auto text-sm text-neutral-500">
            {{ g.tests.length }} Kriterien · {{ g.count }} Fehler
          </span>
        </div>
        <details
          v-for="t in g.tests"
          :key="t.test_id"
          class="group rounded-lg border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900"
        >
          <summary class="cursor-pointer select-none px-4 py-3">
            <div class="flex flex-wrap items-center gap-2">
              <UBadge :color="levelColor(t.level)" variant="soft">{{ levelText(t.level) }}</UBadge>
              <UBadge v-if="t.wcag_level" color="info" variant="soft">{{ t.wcag_level }}</UBadge>
              <UButton
                icon="i-lucide-circle-help"
                color="neutral"
                variant="ghost"
                size="xs"
                class="-my-0.5"
                :aria-label="'Info zu ' + t.title"
                @click.stop="infoTest = infoOf(t)"
              />
              <span class="font-medium">{{ t.title }}</span>
              <span v-if="t.number" class="font-mono text-xs text-neutral-400">{{ t.category }} {{ t.number }}</span>
              <span class="ml-auto text-sm text-neutral-500">{{ t.count }}× auf {{ t.urls.length }} Seite(n)</span>
            </div>
            <ul class="mt-2 flex flex-wrap gap-1.5">
              <li
                v-for="u in t.urls"
                :key="u"
                class="rounded bg-neutral-100 px-2 py-0.5 font-mono text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
              >
                {{ u }}
              </li>
            </ul>
          </summary>
          <div class="border-t border-neutral-200 px-4 py-3 dark:border-neutral-800">
            <ul class="space-y-2">
              <li v-for="(f, i) in t.findings" :key="i" class="text-sm">
                <div class="flex items-start gap-2">
                  <ScreenshotThumb
                    v-if="f.id && f.screenshot"
                    :job-id="results.job_id"
                    :finding="f"
                  />
                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <UBadge v-if="f.wcag_level" color="info" variant="soft" size="sm">{{ f.wcag_level }}</UBadge>
                      <span class="font-medium">
                        {{ f.message }}
                        <span v-if="f.resolution" class="text-xs text-neutral-500">(bei {{ f.resolution }}px)</span>
                      </span>
                    </div>
                    <div class="mt-0.5 truncate font-mono text-xs text-neutral-500">{{ f.url }}</div>
                    <div v-if="f.dom_path" class="font-mono text-xs text-neutral-400">Pfad: {{ f.dom_path }}</div>
                    <div v-if="f.detail" class="text-xs text-neutral-400">{{ f.detail }}</div>
                    <div v-if="stdLabel(f)" class="text-xs text-neutral-400">{{ stdLabel(f) }}</div>
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </details>
      </template>
    </template>
    <div v-else-if="!passed.length" class="rounded-lg border border-neutral-200 p-8 text-center text-neutral-500 dark:border-neutral-800">
      Keine Fehler gefunden — dieser Scan ist fehlerfrei.
    </div>

    <!-- Bestandene Kriterien (grün) -->
    <details
      v-if="passed.length"
      class="group rounded-lg border border-green-200 bg-white dark:border-green-900 dark:bg-green-950/30"
    >
      <summary class="cursor-pointer select-none px-4 py-3">
        <div class="flex flex-wrap items-center gap-2">
          <UBadge color="success" variant="soft">Bestanden</UBadge>
          <span class="font-medium">Bestandene Kriterien</span>
          <span class="ml-auto text-sm text-neutral-500">{{ passed.length }} Kriterien</span>
        </div>
      </summary>
      <ul class="max-h-80 space-y-1 overflow-y-auto border-t border-green-200 px-4 py-3 dark:border-green-900">
        <li
          v-for="t in passed"
          :key="t.test_id"
          class="flex flex-wrap items-center gap-2 rounded bg-green-50 px-2 py-1 text-sm dark:bg-green-950/40"
        >
          <UBadge color="success" variant="soft" size="xs">Bestanden</UBadge>
          <UBadge v-if="t.wcag_level" color="info" variant="soft" size="xs">{{ t.wcag_level }}</UBadge>
          <UButton
            icon="i-lucide-circle-help"
            color="neutral"
            variant="ghost"
            size="xs"
            class="-my-0.5"
            :aria-label="'Info zu ' + t.title"
            @click="infoTest = infoOf(t)"
          />
          <span class="font-medium">{{ t.title }}</span>
          <span v-if="t.number" class="font-mono text-xs text-neutral-400">{{ t.category }} {{ t.number }}</span>
        </li>
      </ul>
    </details>

    <!-- Info-Modal: vollständige Kriterien-Info -->
    <TestInfoModal v-if="infoTest" :test="infoTest" @close="infoTest = null" />
  </div>
</template>
