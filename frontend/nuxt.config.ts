// A11Y Scanner — Frontend-Konfiguration
//
// SPA (ssr: false): Der Nitro-Server liefert das Shell-HTML und proxied
// /api und /ws auf das Backend (API_URL bzw. localhost:8000 im Dev).
// Dadurch ist das Frontend immer same-origin — kein CORS-Problem im
// Produktiv-Container.
export default defineNuxtConfig({
  ssr: false,

  modules: ['@nuxt/ui'],

  nitro: {
    // WebSocket-Support aktivieren: ohne dieses Flag hängt der node-server
    // keinen "upgrade"-Listener an (import.meta._websocket), der WS-Tunnel
    // (server/routes/ws/jobs/[id].ts) bekäme nie die Handshake-Upgrades.
    experimental: {
      websocket: true,
    },
  },

  // Dev-Antworten nie cachen lassen (veraltete Frontends): Ohne
  // Cache-Control-Header speichert der Browser HTML und Module heuristisch
  // und zeigt beim nächsten Besuch einen alten Stand. no-store auf den
  // Vite-Modulen (JS/CSS) + server/plugins/no-cache.ts auf dem Nitro-HTML
  // stellen sicher, dass jeder Seitenladevorgang den aktuellen Code holt.
  vite: {
    server: {
      headers: {
        'Cache-Control': 'no-store',
      },
    },
  },

  css: ['~/assets/css/main.css'],

  devtools: { enabled: false },

  app: {
    head: {
      title: 'A11Y Scanner by G.Kaplick',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Barrierefreiheits-Scanner (BITV 2.0 / WCAG 2.1 / EN 301 549)' },
      ],
    },
  },

  runtimeConfig: {
    apiTarget: process.env.API_URL || 'http://localhost:8000',
  },

  routeRules: {
    '/api/**': { proxy: `${process.env.API_URL || 'http://localhost:8000'}/api/**` },
    // /ws/** ist NICHT als routeRules-Proxy konfiguriert: Nitro-proxies können
    // WebSocket-Upgrades nicht durchreichen (nur HTTP). Der WS-Tunnel wird als
    // eigene Nitro-Server-Route behandelt (server/routes/ws/jobs/[id].ts) —
    // sie verbindet selbst zum Backend und piped beide Richtungen.
  },
})
