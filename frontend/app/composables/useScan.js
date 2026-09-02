/**
 * API-/WebSocket-Client für den A11Y-Scanner.
 *
 * Das Frontend spricht immer same-origin an (Nitro-Proxy leitet /api und /ws
 * ans Backend weiter) — daher hier nur relative Pfade. Alle Aufrufe laufen
 * über `apiFetch`, dessen 401-Handler die Auth-Schicht auf "guest" zurücksetzt
 * (Session abgelaufen → Login).
 *
 * WebSocket: Der WS-Tunnel reicht Cookies nicht ans Backend weiter — deshalb
 * wird vor dem Verbinden ein kurzlebiges Ticket (useAuth.getWsToken) geholt
 * und als `?ws_token=…` an die URL gehängt.
 */
import { apiFetch } from '../utils/apiFetch'

const base = '/api'

export const useScan = () => {
  const createJob = async (payload) => {
    return await apiFetch(`${base}/jobs`, { method: 'POST', body: payload })
  }

  const listJobs = async () => {
    return await apiFetch(`${base}/jobs`)
  }

  const getJob = async (id) => {
    return await apiFetch(`${base}/jobs/${id}`)
  }

  const cancelJob = async (id) => {
    return await apiFetch(`${base}/jobs/${id}/cancel`, { method: 'POST' })
  }

  /** Abgeschlossenen Scan samt Daten (Seiten, Befunde, Test-Aufzeichnungen) löschen. */
  const deleteJob = async (id) => {
    return await apiFetch(`${base}/jobs/${id}`, { method: 'DELETE' })
  }

  const getResults = async (id) => {
    return await apiFetch(`${base}/jobs/${id}/results`)
  }

  const getTests = async () => {
    return await apiFetch(`${base}/tests`)
  }

  const getTestsSummary = async () => {
    return await apiFetch(`${base}/tests/summary`)
  }

  /** Export-URL (TXT-Report); Download über separaten <a>-Klick (siehe download). */
  const exportUrl = (id) => `${base}/jobs/${id}/export/txt`

  /** Trigger einen Datei-Download (Content-Disposition: attachment). */
  const download = (id) => {
    const a = document.createElement('a')
    a.href = exportUrl(id)
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    a.remove()
  }

  /**
   * WebSocket zum Live-Progress eines Jobs.
   * `token` = kurzlebiges WS-Ticket (useAuth.getWsToken); ohne Token wird
   * nicht verbunden. Events kommen als ProgressEvent-JSON; onClose wird auch
   * bei Server-Close aufgerufen (Job fertig → erneutes Laden der Ergebnisse,
   * bzw. nicht autorisiert → Fallback auf REST-Polling).
   */
  const connectWs = (jobId, { token, onEvent, onClose } = {}) => {
    if (!token) return null
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const query = `?ws_token=${encodeURIComponent(token)}`
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/jobs/${jobId}${query}`)
    ws.onmessage = (event) => {
      try {
        onEvent?.(JSON.parse(event.data))
      } catch {
        /* unlesbares Event ignorieren */
      }
    }
    ws.onclose = (e) => onClose?.(e)
    return ws
  }

  return {
    createJob,
    listJobs,
    getJob,
    cancelJob,
    deleteJob,
    getResults,
    getTests,
    getTestsSummary,
    exportUrl,
    download,
    connectWs,
  }
}
