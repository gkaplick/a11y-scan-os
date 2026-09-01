// Schutz gegen veraltete Frontends (Dev-Modus)
//
// Der Nitro-Server (SPA-Shell-HTML) antwortet standardmäßig ohne
// Cache-Control-Header. Der Browser darf solche Antworten heuristisch cachen
// und zeigt beim nächsten Besuch einen ALTEN Stand der Seite — das führte
// wiederholt zu "veralteten Frontends" trotz korrektem aktuellem Code.
//
// no-store erzwingt, dass jede gerenderte Antwort (v. a. das Shell-HTML) bei
// jedem Laden frisch vom Dev-Server kommt. Die Vite-Module (JS/CSS) werden
// zusätzlich über vite.server.headers in der nuxt.config gegen Caching
// geschützt.
export default defineNitroPlugin((nitroApp) => {
  nitroApp.hooks.hook('render:response', (response, _context) => {
    response.headers = response.headers || {}
    response.headers['Cache-Control'] = 'no-store'
  })
})
