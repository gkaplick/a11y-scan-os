<script setup>
/** Fortschrittsanzeige für einen laufenden Job (Balken + aktuelle Seite). */
defineProps({
  job: { type: Object, required: true },
})

const STATUS_TEXT = {
  queued: 'Wartet in der Warteschlange…',
  running: 'Scan läuft',
  done: 'Abgeschlossen',
  failed: 'Fehlgeschlagen',
  canceled: 'Abgebrochen',
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between text-sm">
      <span class="font-medium">
        {{ STATUS_TEXT[job.status] || job.status }}
      </span>
      <span class="tabular-nums text-neutral-500">{{ Math.round(job.progress) }} %</span>
    </div>
    <UProgress :model-value="job.progress" :max="100" color="primary" size="lg" />
    <p v-if="job.current_url" class="truncate font-mono text-xs text-neutral-500">
      {{ job.current_url }}
    </p>
    <p v-if="job.message && job.message !== job.current_url" class="text-xs text-neutral-500">
      {{ job.message }}
    </p>
  </div>
</template>
