<script setup>
/**
 * Vollständige Kriterien-Info als Modal.
 *
 * Öffnet sich aus dem Fragezeichen-Icon eines Tests (Startseiten-Tabelle und
 * Testergebnis) und zeigt alle hinterlegten Infos: Titel, Norm/Nummer, Level,
 * WCAG-Level, Verantwortung sowie die drei Textbausteine der Registry
 * (Was wird geprüft? · Wie wird geprüft? · Lösung). Bewusst schlankes
 * Dialog-Overlay statt Nuxt-UI-UModal (in v3 unzuverlässig).
 */
const props = defineProps({
  test: { type: Object, required: true },
})
const emit = defineEmits(['close'])

const LEVEL_META = {
  MUSS: { color: 'error', label: 'Muss' },
  SOLLTE: { color: 'warning', label: 'Sollte' },
  KANN: { color: 'neutral', label: 'Kann' },
}
const responsibilityLabel = (r) =>
  r === 'technisch' ? 'Technisch' : r === 'redaktionell' ? 'Redaktionell' : r || ''

// Beschreibungstexte sind in der Registry mit Markdown-`**` ausgezeichnet.
const text = (field) => {
  const v = (props.test[field] || '').replace(/\*\*/g, '').trim()
  return v || '—'
}

onMounted(() => {
  const onKey = (e) => { if (e.key === 'Escape') emit('close') }
  window.addEventListener('keydown', onKey)
  onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
})
</script>

<template>
  <div
    class="fixed inset-0 z-50 flex items-center justify-center p-4"
    role="dialog"
    aria-modal="true"
  >
    <div class="absolute inset-0 bg-neutral-900/40" @click="emit('close')" />
    <div class="relative flex max-h-[85vh] w-full max-w-lg flex-col rounded-2xl border border-neutral-200 bg-white shadow-lg dark:border-neutral-800 dark:bg-neutral-900">
      <div class="flex items-start justify-between gap-3 border-b border-neutral-200 px-5 py-4 dark:border-neutral-800">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-1.5">
            <UBadge v-if="test.number" color="neutral" variant="soft" size="sm">
              {{ test.category }} {{ test.number }}
            </UBadge>
            <UBadge
              v-if="test.level && LEVEL_META[test.level]"
              :color="LEVEL_META[test.level].color"
              variant="soft"
              size="sm"
            >
              {{ LEVEL_META[test.level].label }}
            </UBadge>
            <UBadge v-if="test.wcag_level" color="info" variant="soft" size="sm">
              WCAG {{ test.wcag_level }}
            </UBadge>
            <UBadge v-if="test.responsibility" color="neutral" variant="soft" size="sm">
              {{ responsibilityLabel(test.responsibility) }}
            </UBadge>
          </div>
          <h3 class="mt-1.5 text-base font-semibold">{{ test.title }}</h3>
          <p v-if="test.test_id" class="font-mono text-xs text-neutral-400">{{ test.test_id }}</p>
        </div>
        <UButton
          color="neutral"
          variant="ghost"
          icon="i-lucide-x"
          :aria-label="'Dialog schließen'"
          @click="emit('close')"
        />
      </div>
      <div class="min-h-0 flex-1 space-y-4 overflow-y-auto px-5 py-4">
        <section>
          <h4 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Was wird geprüft?</h4>
          <p class="mt-1 whitespace-pre-wrap text-sm text-neutral-700 dark:text-neutral-300">{{ text('description') }}</p>
        </section>
        <section>
          <h4 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Wie wird geprüft?</h4>
          <p class="mt-1 whitespace-pre-wrap text-sm text-neutral-700 dark:text-neutral-300">{{ text('test_hint') }}</p>
        </section>
        <section>
          <h4 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Lösung</h4>
          <p class="mt-1 whitespace-pre-wrap text-sm text-neutral-700 dark:text-neutral-300">{{ text('solution') }}</p>
        </section>
      </div>
    </div>
  </div>
</template>
