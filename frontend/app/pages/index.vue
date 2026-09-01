<script setup>
useHead({ title: 'A11Y Scanner by G.Kaplick' })
</script>

<template>
  <div class="space-y-10">
    <section class="text-center">
      <h1 class="text-3xl font-bold sm:text-4xl">Barrierefreiheits-Scan für Websites</h1>
      <p class="mx-auto mt-3 max-w-2xl text-neutral-600 dark:text-neutral-400">
        Automatisierte Prüfung auf BITV 2.0, WCAG 2.1 und EN 301 549.
        URL eintragen, Scan starten, Live-Fortschritt verfolgen und das Ergebnis
        nach Test oder nach Seite auswerten — inklusive TXT-Report-Export.
      </p>
    </section>

    <section class="mx-auto max-w-2xl">
      <div class="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
        <UrlForm />
      </div>
    </section>

    <section>
      <CoverageMap />
    </section>
  </div>
</template>
