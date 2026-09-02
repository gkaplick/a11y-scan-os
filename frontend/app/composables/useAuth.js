/**
 * Auth-Zustand des Frontends (Login/Logout/me + WS-Ticket).
 *
 * Bewusst **keine** Persistenz (kein localStorage): Der Zustand lebt nur im
 * Speicher; ein Reload prüft `GET /api/auth/me` über das httpOnly-Cookie.
 * Verlorene/abgelaufene Sessions fangen die 401-Handler von `apiFetch` ab
 * und setzen den Zustand zurück auf "guest".
 */
import { ref } from 'vue'
import { apiFetch, registerUnauthorizedHandler } from '../utils/apiFetch'

const BASE = '/api/auth'

const authState = ref('loading') // 'loading' | 'guest' | 'authed'
const authUser = ref(null)

function setGuest() {
  authState.value = 'guest'
  authUser.value = null
}

function applyUser(user) {
  if (user) {
    authUser.value = user
    authState.value = 'authed'
  } else {
    setGuest()
  }
}

/** Zentrale 401-Behandlung: Session abgelaufen → zurück zum Login. */
registerUnauthorizedHandler(() => {
  if (authState.value === 'authed') setGuest()
})

/** Beim App-Start: Bestandssession über /me prüfen. */
async function init() {
  if (authState.value === 'authed') return authUser.value
  authState.value = 'loading'
  try {
    const user = await apiFetch(`${BASE}/me`)
    applyUser(user)
  } catch {
    applyUser(null)
  }
  return authUser.value
}

/** Login → bei Erfolg authed (wirft bei falschen Daten, Meldung zeigt die UI). */
async function login(username, password) {
  const user = await apiFetch(`${BASE}/login`, {
    method: 'POST',
    body: { username, password },
  })
  applyUser(user)
  return user
}

/** Logout → Session im Backend widerrufen + lokal auf guest. */
async function logout() {
  try {
    await apiFetch(`${BASE}/logout`, { method: 'POST' })
  } catch {
    /* Session existiert ggf. nicht mehr — lokal trotzdem abmelden */
  }
  setGuest()
}

/** Kurzlebiges Einmal-Ticket für den WebSocket-Live-Progress. */
async function getWsToken() {
  const { token } = await apiFetch(`${BASE}/ws-token`)
  return token
}

export const useAuth = () => ({
  status: authState,
  user: authUser,
  init,
  login,
  logout,
  getWsToken,
})
