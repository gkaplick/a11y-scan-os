<script setup>
/**
 * Scan-Formular: URL + Suite + Optionen (max. Seiten, HTACCESS).
 * Startet per POST /api/jobs einen Scan und navigiert zur Detailseite.
 */
const { createJob } = useScan()
const { disabled, clearAll } = useDisabledTests()
const { assessments } = useManualAssessments()
const router = useRouter()

const url = ref('')
const maxPages = ref(1)
const useAuth = ref(false)
const htaccessUser = ref('')
const htaccessPw = ref('')

const loading = ref(false)
const error = ref('')

// Anzahl der als "nicht relevant" deaktivierten Tests (für den Hinweis im Formular)
const disabledCount = computed(() => disabled.value.size)

const start = async () => {
  error.value = ''
  if (!url.value.trim()) {
    error.value = 'Bitte eine gültige URL eingeben (z. B. https://example.com).'
    return
  }
  try {
    loading.value = true
    const job = await createJob({
      url: url.value.trim(),
      // Immer die volle Suite (BITV 2.0 + WCAG 2.1 + EN 301 549) scannen;
      // einzelne Kriterien deaktiviert man über die Tabelle darunter.
      suite: 'all',
      max_pages: maxPages.value > 0 ? maxPages.value : null,
      htaccess_user: useAuth.value && htaccessUser.value ? htaccessUser.value : null,
      htaccess_pw: useAuth.value && htaccessPw.value ? htaccessPw.value : null,
      disabled_test_ids: [...disabled.value],
      manual_assessments: { ...assessments.value },
    })
    await router.push(`/jobs/${job.id}`)
  } catch (e) {
    error.value = e?.data?.detail || 'Scan konnte nicht gestartet werden.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form @submit.prevent="start" class="space-y-4">
    <div>
      <label class="mb-1 block text-sm font-medium">URL des Projekts</label>
      <UInput
        v-model="url"
        type="url"
        placeholder="https://example.com"
        size="lg"
        class="w-full"
        :disabled="loading"
      />
    </div>

    <div>
      <label class="mb-1 block text-sm font-medium">Max. Seiten (0 = unbegrenzt)</label>
      <UInput
        v-model.number="maxPages"
        type="number"
        min="0"
        size="lg"
        class="w-full"
        :disabled="loading"
      />
    </div>

    <div class="rounded-lg border border-neutral-200 p-3 dark:border-neutral-700">
      <UCheckbox v-model="useAuth" label="HTACCESS-Zugangsdaten angeben (optional)" :disabled="loading" />
      <div v-if="useAuth" class="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <label class="mb-1 block text-sm font-medium">Benutzer</label>
          <UInput v-model="htaccessUser" autocomplete="username" size="sm" class="w-full" />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium">Passwort</label>
          <UInput v-model="htaccessPw" type="password" autocomplete="current-password" size="sm" class="w-full" />
        </div>
      </div>
    </div>

    <div
      v-if="disabledCount"
      class="flex items-center justify-between gap-2 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 dark:border-sky-900 dark:bg-sky-950/40"
    >
      <span class="text-sm text-sky-700 dark:text-sky-300">
        {{ disabledCount }} Test(s) als nicht relevant deaktiviert — werden übersprungen.
      </span>
      <UButton size="xs" color="neutral" variant="soft" @click="clearAll">
        Alle aktivieren
      </UButton>
    </div>

    <UAlert v-if="error" color="error" :title="error" icon="i-lucide-circle-alert" />

    <UButton
      type="submit"
      color="primary"
      size="lg"
      :loading="loading"
      :disabled="loading"
      class="w-full"
      icon="i-lucide-play"
    >
      Scan starten
    </UButton>
  </form>
</template>
