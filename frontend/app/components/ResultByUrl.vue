<script setup>
/** Ergebnis-Perspektive 2: je URL → gefundene Fehler. */
defineProps({
  results: { type: Object, required: true },
})

const statusText = (u) => {
  if (u.http_status === 404) return '404'
  if (u.http_status) return String(u.http_status)
  return u.ok ? 'OK' : 'Fehler'
}
const statusColor = (u) => {
  if (u.http_status === 404) return 'warning'
  if (!u.ok) return 'error'
  return 'success'
}
const levelColor = (level) => ({ MUSS: 'error', SOLLTE: 'warning', KANN: 'neutral' })[level] || 'neutral'
// Befunde einer Seite nach Dringlichkeit sortieren (MUSS → SOLLTE → KANN).
const levelRank = (level) => ({ MUSS: 0, SOLLTE: 1, KANN: 2 })[level] ?? 3
const sortedFindings = (u) =>
  [...u.findings].sort((a, b) => levelRank(a.level) - levelRank(b.level))
const stdLabel = (f) => {
  if (!f.category) return ''
  return f.number ? `${f.category} ${f.number}` : f.category
}
</script>

<template>
  <div v-if="!results.by_url.length" class="rounded-lg border border-neutral-200 p-8 text-center text-neutral-500 dark:border-neutral-800">
    Keine Seiten geprüft.
  </div>

  <div v-else class="space-y-3">
    <details
      v-for="u in results.by_url"
      :key="u.url"
      class="group rounded-lg border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900"
      :open="u.finding_count > 0"
    >
      <summary class="cursor-pointer select-none px-4 py-3">
        <div class="flex flex-wrap items-center gap-2">
          <UBadge :color="statusColor(u)" variant="soft">HTTP {{ statusText(u) }}</UBadge>
          <span class="font-mono text-sm">{{ u.url }}</span>
          <span class="ml-auto text-sm text-neutral-500">
            {{ u.finding_count }} Fehler
          </span>
        </div>
      </summary>
      <div class="border-t border-neutral-200 px-4 py-3 dark:border-neutral-800">
        <div v-if="!u.findings.length" class="text-sm text-neutral-500">
          Keine Fehler auf dieser Seite.
        </div>
        <ul v-else class="space-y-2">
          <li v-for="(f, i) in sortedFindings(u)" :key="i" class="text-sm">
            <div class="flex items-start gap-2">
              <ScreenshotThumb
                v-if="f.id && f.screenshot"
                :job-id="results.job_id"
                :finding="f"
              />
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <UBadge :color="levelColor(f.level)" variant="soft" size="sm">{{ f.level }}</UBadge>
                  <UBadge v-if="f.wcag_level" color="info" variant="soft" size="sm">{{ f.wcag_level }}</UBadge>
                  <span class="font-medium">{{ f.message }}</span>
                  <span v-if="f.resolution" class="text-xs text-neutral-500">(bei {{ f.resolution }}px)</span>
                </div>
                <div v-if="f.dom_path" class="font-mono text-xs text-neutral-500">Pfad: {{ f.dom_path }}</div>
                <div v-if="f.detail" class="text-xs text-neutral-400">{{ f.detail }}</div>
                <div v-if="stdLabel(f)" class="text-xs text-neutral-400">{{ stdLabel(f) }}</div>
              </div>
            </div>
          </li>
        </ul>
      </div>
    </details>
  </div>
</template>
