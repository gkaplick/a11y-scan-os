<template>
  <UApp>
    <div class="min-h-screen bg-neutral-50 text-neutral-900 dark:bg-neutral-900 dark:text-neutral-100">
      <header class="border-b border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
        <div class="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-3">
          <NuxtLink to="/" class="flex items-center gap-2 text-lg font-semibold">
            <UIcon name="i-lucide-clipboard-check" class="text-primary-500" />
            <span class="flex flex-col leading-tight">
              <span>A11Y Scanner</span>
              <span class="text-xs font-normal text-neutral-500 dark:text-neutral-400">by G.Kaplick</span>
            </span>
          </NuxtLink>
          <nav class="flex items-center gap-1 text-sm">
            <NuxtLink to="/" class="rounded-md px-3 py-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800">
              Neuer Scan
            </NuxtLink>
            <NuxtLink to="/jobs" class="rounded-md px-3 py-1.5 hover:bg-neutral-100 dark:hover:bg-neutral-800">
              Scans
            </NuxtLink>
          </nav>
        </div>
      </header>
      <main class="mx-auto w-full max-w-6xl px-4 py-8">
        <NuxtPage />
      </main>
      <footer class="border-t border-neutral-200 py-4 text-center text-xs text-neutral-500 dark:border-neutral-800">
        <div class="mx-auto w-full max-w-6xl px-4">
          BITV 2.0 · WCAG 2.1 · EN 301 549 — automatisierter Barrierefreiheits-Scanner
        </div>
      </footer>
    </div>
  </UApp>
</template>
