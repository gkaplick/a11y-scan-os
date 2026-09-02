/**
 * Gemeinsamer API-Fetch mit zentraler 401-Behandlung.
 *
 * Alle App-Aufrufe laufen über `apiFetch` (statt des Auto-Import-`$fetch`),
 * damit ein abgelaufenes Session-Cookie (HTTP 401) überall einheitlich die
 * Auth-Schicht auf "guest" zurückfallen lässt → Login-Screen erscheint.
 *
 * `registerUnauthorizedHandler` wird von useAuth registriert (bewusst kein
 * Import von useAuth hier — das würde einen Zirkularimport erzeugen).
 */
import { $fetch } from 'ofetch'

const unauthorizedHandlers = new Set()

export function registerUnauthorizedHandler(handler) {
  unauthorizedHandlers.add(handler)
  // Gibt eine Deregistrierungs-Funktion zurück.
  return () => unauthorizedHandlers.delete(handler)
}

export const apiFetch = $fetch.create({
  onResponseError({ response }) {
    if (response && response.status === 401) {
      unauthorizedHandlers.forEach((handler) => {
        try {
          handler()
        } catch {
          /* Handler-Fehler dürfen den eigentlichen Fehler nicht verschlucken */
        }
      })
    }
  },
})
