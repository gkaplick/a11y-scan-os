// WebSocket-Tunnel: leitet /ws/jobs/{id} auf das Backend weiter (crossws).
//
// Nitro-routeRules-Proxies können WebSocket-Upgrades nicht durchreichen (nur
// HTTP) — daher kommt hier ein eigener Handler: Er öffnet zum selben Pfad eine
// Client-WebSocket-Verbindung zum API-Service (API_URL, intern im Compose-
// Netzwerk ws://api:8000) und piped die Nachrichten in beide Richtungen.
//
// Der Client (useScan.js) spricht damit weiterhin same-origin an — der Browser
// verbindet sich nur zu :3001, das Upgrade passiert innerhalb des Containers.
import { defineWebSocketHandler } from 'h3'

const API_URL = process.env.API_URL || 'http://localhost:8000'
const API_WS = API_URL.replace(/^http/, 'ws') // http:// → ws://, https:// → wss://

export default defineWebSocketHandler({
  open(peer) {
    // peer.request.url ist die vollständige Anfrage-URL (mit Pfad + Query) —
    // denselben Pfad sprechen wir auch auf dem Backend an.
    const reqUrl = new URL(peer.request.url, 'http://localhost')
    const upstreamUrl = API_WS + reqUrl.pathname + reqUrl.search

    const upstream = new WebSocket(upstreamUrl)
    peer.context.upstream = upstream
    peer.context.upstreamClosed = false

    upstream.onmessage = (event) => {
      if (!peer.context.upstreamClosed) peer.send(event.data)
    }
    // Backend abgestürzt / Verbindung zu api:8000 scheitert → Browser-Socket
    // sauber beenden, damit useScan.js über onClose zum REST-Polling wechselt.
    upstream.onerror = () => {
      if (!peer.context.upstreamClosed) {
        peer.context.upstreamClosed = true
        peer.close()
      }
    }
    upstream.onclose = () => {
      if (!peer.context.upstreamClosed) {
        peer.context.upstreamClosed = true
        peer.close()
      }
    }
  },
  message(peer, message) {
    const upstream = peer.context.upstream
    if (upstream && upstream.readyState === WebSocket.OPEN) {
      upstream.send(message.arrayBuffer())
    }
  },
  close(peer) {
    const upstream = peer.context.upstream
    if (upstream && !peer.context.upstreamClosed) {
      peer.context.upstreamClosed = true
      try {
        upstream.close()
      } catch {
        /* bereits geschlossen */
      }
    }
  },
})
