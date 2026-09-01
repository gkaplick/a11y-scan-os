<script setup>
useHead({ title: 'Scans — A11Y Scanner by G.Kaplick' })
const { listJobs, cancelJob, deleteJob } = useScan()

const jobs = ref([])
const loading = ref(true)
const error = ref('')
const cancelling = ref({})
const deleting = ref({})
const confirmDelete = ref(null) // Job, dessen Löschung bestätigt werden soll

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    jobs.value = await listJobs()
  } catch (e) {
    error.value = e?.data?.detail || 'Job-Liste konnte nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

const refreshTimer = ref(null)
onUnmounted(() => clearInterval(refreshTimer.value))

// Live-Fortschritt der Liste: alle 3 s aktualisieren, solange aktive Jobs da sind.
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
const time = (iso) => (iso ? new Date(iso).toLocaleString('de-DE') : '—')

const active = computed(() => jobs.value.some((j) => j.status === 'queued' || j.status === 'running'))

watch(active, (isActive) => {
  clearInterval(refreshTimer.value)
  if (isActive) {
    refreshTimer.value = setInterval(async () => {
      const fresh = await listJobs().catch(() => null)
      if (fresh) jobs.value = fresh
    }, 3000)
  }
})

const cancel = async (job) => {
  if (cancelling.value[job.id]) return
  cancelling.value = { ...cancelling.value, [job.id]: true }
  try {
    await cancelJob(job.id)
    await load()
  } catch (e) {
    error.value = e?.data?.detail || 'Abbrechen fehlgeschlagen.'
  } finally {
    cancelling.value = { ...cancelling.value, [job.id]: false }
  }
}

const remove = async (job) => {
  if (deleting.value[job.id]) return
  deleting.value = { ...deleting.value, [job.id]: true }
  try {
    await deleteJob(job.id)
    confirmDelete.value = null
    await load()
  } catch (e) {
    error.value = e?.data?.detail || 'Löschen fehlgeschlagen.'
  } finally {
    deleting.value = { ...deleting.value, [job.id]: false }
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">Scans</h1>
      <UButton color="primary" icon="i-lucide-plus" to="/">Neuer Scan</UButton>
    </div>

    <UAlert v-if="error" color="error" :title="error" icon="i-lucide-circle-alert" />

    <div v-if="loading && !jobs.length" class="py-12 text-center text-neutral-500">Lade Scans…</div>

    <div v-else-if="!jobs.length" class="rounded-lg border border-neutral-200 p-12 text-center text-neutral-500 dark:border-neutral-800">
      Noch keine Scans. <NuxtLink to="/" class="text-primary-500 underline">Jetzt einen starten.</NuxtLink>
    </div>

    <div v-else class="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
      <table class="w-full text-sm">
        <thead class="bg-neutral-100 text-left dark:bg-neutral-800">
          <tr>
            <th class="px-3 py-2 font-medium">Status</th>
            <th class="px-3 py-2 font-medium">Projekt</th>
            <th class="px-3 py-2 font-medium">Suite</th>
            <th class="px-3 py-2 font-medium">Fortschritt</th>
            <th class="px-3 py-2 font-medium">Seiten</th>
            <th class="px-3 py-2 font-medium">Fehler</th>
            <th class="px-3 py-2 font-medium">Erstellt</th>
            <th class="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="j in jobs"
            :key="j.id"
            class="border-t border-neutral-200 dark:border-neutral-800"
          >
            <td class="px-3 py-2">
              <UBadge :color="STATUS_COLOR[j.status]" variant="soft">{{ STATUS_TEXT[j.status] || j.status }}</UBadge>
            </td>
            <td class="max-w-64 truncate px-3 py-2 font-mono text-xs">{{ j.url }}</td>
            <td class="px-3 py-2 whitespace-nowrap">
              <UBadge :color="j.suite === 'all' ? 'neutral' : 'primary'" variant="soft" size="sm">
                {{ j.suite === 'all' ? 'BITV 2.0 + WCAG 2.1' : (j.suite === 'wcag' ? 'WCAG 2.1' : 'BITV 2.0') }}
              </UBadge>
            </td>
            <td class="w-40 px-3 py-2">
              <!-- Nur laufende/wartende Scans zeigen einen Ladebalken; abgeschlossene
                   haben keinen Ladebalken mehr. Nuxt UI v3: UProgress nutzt
                   modelValue (nicht value) — sonst bleibt der Balken indeterminate. -->
              <UProgress
                v-if="j.status === 'queued' || j.status === 'running'"
                :model-value="j.progress"
                :max="100"
                color="primary"
              />
            </td>
            <td class="px-3 py-2 text-center tabular-nums">{{ j.page_count }}</td>
            <td class="px-3 py-2 text-center tabular-nums">{{ j.finding_count }}</td>
            <td class="px-3 py-2 whitespace-nowrap text-neutral-500">{{ time(j.created_at) }}</td>
            <td class="px-3 py-2 whitespace-nowrap text-right">
              <NuxtLink :to="`/jobs/${j.id}`" class="text-primary-500 underline">Öffnen</NuxtLink>
              <UButton
                v-if="j.status === 'queued' || j.status === 'running'"
                color="neutral"
                variant="ghost"
                size="xs"
                icon="i-lucide-square"
                :loading="cancelling[j.id]"
                class="ml-2"
                title="Scan abbrechen"
                @click="cancel(j)"
              />
              <UButton
                v-if="['done', 'failed', 'canceled'].includes(j.status)"
                color="neutral"
                variant="ghost"
                size="xs"
                icon="i-lucide-trash-2"
                :loading="deleting[j.id]"
                class="ml-2"
                title="Scan löschen"
                @click="confirmDelete = j"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Lösch-Bestätigung als eigenes Modal: Nuxt UI v3 UModal ist in dieser
         Version unzuverlässig (Default-Slot = Trigger, Dialog öffnet nicht),
         daher ein schlankes, selbstgerendertes Dialog-Overlay. -->
    <div
      v-if="confirmDelete"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
    >
      <div class="absolute inset-0 bg-neutral-900/40" @click="confirmDelete = null" />
      <div class="relative w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-5 shadow-lg dark:border-neutral-800 dark:bg-neutral-900">
        <h3 class="text-base font-semibold">Scan löschen?</h3>
        <p class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
          Der Scan für <b class="text-neutral-900 dark:text-neutral-100">{{ confirmDelete.url }}</b>
          wird samt allen Daten (Seiten, Befunde, Test-Aufzeichnungen)
          unwiderruflich gelöscht.
        </p>
        <div class="mt-4 flex justify-end gap-2">
          <UButton color="neutral" variant="soft" @click="confirmDelete = null">
            Abbrechen
          </UButton>
          <UButton
            color="error"
            icon="i-lucide-trash-2"
            :loading="deleting[confirmDelete.id]"
            @click="remove(confirmDelete)"
          >
            Löschen
          </UButton>
        </div>
      </div>
    </div>
  </div>
</template>
