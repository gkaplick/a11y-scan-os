<script setup>
/**
 * Element-Screenshot eines Befunds: 80×80-Thumbnail mit minimaler Lightbox.
 *
 * Klick auf das Thumbnail öffnet eine Lightbox mit dem ~400×400-Original;
 * schließen über Backdrop-Klick, Esc oder das X. Existiert kein Screenshot
 * (der Scan konnte den Locator des Elements nicht auflösen), blendet sich das
 * Thumbnail über den @error-Handler selbst aus — die Befundzeile bleibt
 * sonst unverändert.
 *
 * Die URL ist same-origin über den Nitro-Proxy (/api/** → Backend), daher
 * kein Fetch über den useScan-Composable nötig.
 */
const props = defineProps({
  jobId: { type: String, required: true },
  finding: { type: Object, required: true },
})

const src = computed(() => `/api/jobs/${props.jobId}/screenshots/${props.finding.id}.png`)
const available = ref(true)
const open = ref(false)

function closeLightbox() {
  open.value = false
  document.removeEventListener('keydown', closeLightbox)
}
function openLightbox() {
  open.value = true
  document.addEventListener('keydown', closeLightbox)
}
onUnmounted(() => document.removeEventListener('keydown', closeLightbox))
</script>

<template>
  <div class="shrink-0">
    <img
      v-if="available"
      :src="src"
      alt="Screenshot des betroffenen Elements"
      title="Screenshot vergrößern"
      class="h-20 w-20 cursor-zoom-in rounded-md border border-neutral-200 bg-neutral-100 object-cover dark:border-neutral-700 dark:bg-neutral-800"
      @error="available = false"
      @click="openLightbox"
    />

    <!-- Minimale Lightbox: Klick auf Backdrop / Esc / X schließt -->
    <div
      v-if="open"
      class="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Screenshot vergrößern"
      @click="closeLightbox"
    >
      <div class="absolute inset-0 bg-neutral-900/70" />
      <div class="relative" @click.stop>
        <img
          :src="src"
          alt="Screenshot des betroffenen Elements"
          class="max-h-[85vh] max-w-[85vw] rounded-lg border border-neutral-200 bg-white object-contain shadow-2xl dark:border-neutral-700"
        />
        <UButton
          icon="i-lucide-x"
          color="neutral"
          variant="solid"
          size="sm"
          class="absolute -right-3 -top-3"
          aria-label="Schließen"
          @click="closeLightbox"
        />
      </div>
    </div>
  </div>
</template>
