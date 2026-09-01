<script setup>
/**
 * Kurzfassung der drei Testsysteme (BITV / WCAG / EN 301 549) oben im
 * Testergebnis: Gesamturteil je System + Aufschlüsselung der Kriterien.
 *
 * BITV/EN sind binär (bestanden/nicht bestanden; „nicht anwendbar" zählt als
 * bestanden) und zeigen Erfüllt/Nicht erfüllt mit Fortschrittsbalken und Prozent.
 * WCAG ist abgestuft über das erzielte Konformitätsniveau (A/AA/AAA) mit
 * Level-Aufschlüsselung. Manuelle Kriterien werden als „nicht automatisiert"
 * ausgewiesen.
 */
const props = defineProps({
  systems: { type: Array, default: () => [] },
})

const SYSTEM_ORDER = ['BITV', 'WCAG', 'EN 301 549']
const sorted = computed(() =>
  [...props.systems].sort(
    (a, b) => SYSTEM_ORDER.indexOf(a.system) - SYSTEM_ORDER.indexOf(b.system),
  ),
)

const urteilBadge = (s) => {
  if (s.urteil === 'nicht bestanden') return { label: 'Nicht bestanden', color: 'error', icon: 'i-lucide-x-circle' }
  if (s.urteil === 'bestanden') return { label: 'Bestanden', color: 'success', icon: 'i-lucide-check-circle' }
  return { label: 'Nicht bewertbar', color: 'neutral', icon: 'i-lucide-help-circle' }
}

const niveauBadge = (s) => {
  if (!s.niveau) return null
  if (s.niveau === 'kein Level erfüllt') return { label: 'Kein Level', color: 'error' }
  return { label: `Level ${s.niveau}`, color: { A: 'warning', AA: 'success', AAA: 'primary' }[s.niveau] || 'neutral' }
}

// Level-Aufschlüsselung als Tabelle: WCAG nach Konformitätsstufe (A/AA/AAA).
// Jede Zeile: Anzahl + Quote. (BITV/EN sind binär und haben keine
// Aufschlüsselung mehr — siehe block unten.)
const LEVEL_NAME = { A: 'Minimum', AA: 'Standard', AAA: 'Erweitert' }
const levelName = (lv) => LEVEL_NAME[lv] || ''
// Anzeige der ersten Spalte: „A Minimum“ / „AA Standard“ / „AAA Erweitert“.
const levelCell = (lv) => ({ code: lv, desc: levelName(lv) })
const quote = (lv) => {
  const total = lv.gesamt || 0
  return total ? Math.round((lv.bestanden / total) * 100) : 0
}
const barColor = (lv) => {
  const q = quote(lv)
  if (q === 100) return 'bg-success'
  if (q >= 60) return 'bg-warning'
  return 'bg-error'
}
// Summenzeile über alle Level der Aufschlüsselung.
const wcagTotal = (s, key) => s.level_verteilung?.reduce((n, lv) => n + (lv[key] || 0), 0) || 0
const totalQuote = (s) => {
  const gesamt = wcagTotal(s, 'gesamt')
  return gesamt ? Math.round((wcagTotal(s, 'bestanden') / gesamt) * 100) : 0
}
const totalBarColor = (s) => {
  const q = totalQuote(s)
  if (q === 100) return 'bg-success'
  if (q >= 60) return 'bg-warning'
  return 'bg-error'
}

// BITV/EN: Erfolgsquote über die bewerteten Kriterien (bestanden vs. nicht
// bestanden; „nicht automatisiert" fließt nicht in die Quote ein).
const quoteSystem = (s) => {
  const bewertet = (s.bestanden || 0) + (s.nicht_bestanden || 0)
  return bewertet ? Math.round((s.bestanden / bewertet) * 100) : 0
}
const barSystemColor = (s) => {
  const q = quoteSystem(s)
  if (q === 100) return 'bg-success'
  if (q >= 60) return 'bg-warning'
  return 'bg-error'
}
</script>

<template>
  <div v-if="systems.length" class="mb-6 grid gap-4 sm:grid-cols-3">
    <div
      v-for="s in sorted"
      :key="s.system"
      class="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-900"
    >
      <div class="mb-2 flex items-center justify-between gap-2">
        <span class="text-sm font-semibold">{{ s.system }}</span>
        <UBadge :color="urteilBadge(s).color" variant="soft">
          {{ urteilBadge(s).label }}
        </UBadge>
      </div>

      <UBadge
        v-if="s.system === 'WCAG' && niveauBadge(s)"
        :color="niveauBadge(s).color"
        variant="outline"
        size="sm"
        class="mb-3"
      >
        Konformitätsniveau: {{ niveauBadge(s).label }}
      </UBadge>

      <!-- BITV/EN: Erfüllt/Nicht erfüllt + Fortschrittsbalken + Prozent -->
      <div v-if="s.system !== 'WCAG'" class="mt-3">
        <div class="flex items-center justify-between text-xs">
          <span class="flex items-center gap-1.5">
            <span class="h-2 w-2 rounded-full bg-success" />
            <span class="text-neutral-500">Erfüllt</span>
            <b class="tabular-nums text-success dark:text-success">{{ s.bestanden }}</b>
          </span>
          <span class="flex items-center gap-1.5">
            <span class="h-2 w-2 rounded-full bg-error" />
            <span class="text-neutral-500">Nicht erfüllt</span>
            <b class="tabular-nums text-error dark:text-error">{{ s.nicht_bestanden }}</b>
          </span>
        </div>
        <div class="mt-2 flex items-center gap-2">
          <div class="h-2.5 flex-1 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
            <div :class="['h-full rounded-full', barSystemColor(s)]" :style="{ width: quoteSystem(s) + '%' }" />
          </div>
          <span class="w-12 text-right text-lg font-bold tabular-nums text-neutral-900 dark:text-neutral-100">
            {{ quoteSystem(s) }}%
          </span>
        </div>
        <p v-if="s.nicht_automatisiert > 0" class="mt-1.5 text-xs text-neutral-400 dark:text-neutral-500">
          {{ s.nicht_automatisiert }} nicht automatisiert (manuell zu prüfen)
        </p>
        <p v-if="s.system === 'EN 301 549'" class="mt-1 text-xs text-neutral-400 dark:text-neutral-500">
          Nur verbindliche Kriterien (WCAG A/AA + EN-Kapitel 5–12) bestimmen das Urteil.
          <template v-if="s.erweitert > 0"> {{ s.erweitert }} erweitert (AAA) informatorisch.</template>
        </p>
      </div>

      <!-- WCAG: Level-Aufschlüsselung (A/AA/AAA) -->
      <table
        v-if="s.system === 'WCAG' && s.level_verteilung?.length"
        class="mt-3 w-full border-t border-neutral-100 text-xs dark:border-neutral-800"
      >
        <thead>
          <tr class="text-left text-neutral-400">
            <th class="py-1 pr-2 font-medium">Level</th>
            <th class="py-1 pr-2 font-medium text-success dark:text-success">Erfüllt</th>
            <th class="py-1 pr-2 font-medium text-error dark:text-error">Verletzt</th>
            <th class="py-1 text-right font-medium">Quote</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="lv in s.level_verteilung"
            :key="lv.level"
            class="border-t border-neutral-100 dark:border-neutral-800"
          >
            <td class="py-1.5 pr-2">
              <b class="text-neutral-900 dark:text-neutral-100">{{ levelCell(lv.level).code }}</b>
              <span v-if="levelCell(lv.level).desc" class="ml-1 text-neutral-400">{{ levelCell(lv.level).desc }}</span>
            </td>
            <td class="py-1.5 pr-2 tabular-nums text-success dark:text-success">{{ lv.bestanden }}</td>
            <td class="py-1.5 pr-2 tabular-nums text-error dark:text-error">{{ lv.nicht_bestanden }}</td>
            <td class="py-1.5">
              <div class="flex items-center justify-end gap-1.5">
                <div class="h-1.5 w-14 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
                  <div :class="['h-full rounded-full', barColor(lv)]" :style="{ width: quote(lv) + '%' }" />
                </div>
                <span class="w-9 text-right tabular-nums text-neutral-500">{{ quote(lv) }}%</span>
              </div>
            </td>
          </tr>
        </tbody>
        <!-- Summenzeile über alle Level -->
        <tfoot>
          <tr class="border-t-2 border-neutral-200 dark:border-neutral-700">
            <td class="py-1.5 pr-2 font-semibold text-neutral-900 dark:text-neutral-100">Summe</td>
            <td class="py-1.5 pr-2 tabular-nums font-semibold text-success dark:text-success">{{ wcagTotal(s, 'bestanden') }}</td>
            <td class="py-1.5 pr-2 tabular-nums font-semibold text-error dark:text-error">{{ wcagTotal(s, 'nicht_bestanden') }}</td>
            <td class="py-1.5">
              <div class="flex items-center justify-end gap-1.5">
                <div class="h-1.5 w-14 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
                  <div :class="['h-full rounded-full', totalBarColor(s)]" :style="{ width: totalQuote(s) + '%' }" />
                </div>
                <span class="w-9 text-right tabular-nums text-neutral-500">{{ totalQuote(s) }}%</span>
              </div>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</template>
