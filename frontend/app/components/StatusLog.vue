<script setup>
/** Live-Log der Progress-Events eines Jobs (autoscrollt ans Ende). */
const props = defineProps({
  events: { type: Array, required: true },
})

const box = ref(null)

watch(
  () => props.events.length,
  () => {
    nextTick(() => {
      if (box.value) box.value.scrollTop = box.value.scrollHeight
    })
  },
)

const time = (ev) => {
  if (!ev.at) return ''
  const d = new Date(ev.at)
  return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<template>
  <div class="rounded-lg border border-neutral-200 bg-neutral-950 p-3 dark:border-neutral-800">
    <div ref="box" class="max-h-72 space-y-1 overflow-y-auto font-mono text-xs leading-relaxed">
      <div v-if="!events.length" class="text-neutral-500">Warte auf erste Ereignisse…</div>
      <!-- Log-Meldungen mit \n (z. B. „Seite geprüft: N\nFehler auf dieser
           Seite: M") als Zeilenumbruch rendern statt wörtlich. -->
      <div v-for="(ev, i) in events" :key="i" class="flex gap-2">
        <span class="shrink-0 text-neutral-500">{{ time(ev) }}</span>
        <span
          :class="{
            'text-emerald-400': ev.type === 'done',
            'text-red-400': ev.type === 'error',
            'text-sky-300': ev.type === 'page',
            'text-neutral-300': ev.type === 'log' || ev.type === 'status',
            'whitespace-pre-line': ev.type === 'log',
          }"
        >
          {{ ev.message }}
        </span>
      </div>
    </div>
  </div>
</template>
