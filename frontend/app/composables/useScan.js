/**
 * API-/WebSocket-Client für den A11Y-Scanner.
 *
 * Das Frontend spricht immer same-origin an (Nitro-Proxy leitet /api und /ws
 * ans Backend weiter) — daher hier nur relative Pfade.
 */

const base = '/api'

export const useScan = () => {
  const createJob = async (payload) => {
    return await $fetch(`${base}/jobs`, { method: 'POST', body: payload })
  }

  const listJobs = async () => {
    return await $fetch(`${base}/jobs`)
  }

  const getJob = async (id) => {
    return await $fetch(`${base}/jobs/${id}`)
  }

  const cancelJob = async (id) => {
    return await $fetch(`${base}/jobs/${id}/cancel`, { method: 'POST' })
  }

  /** Abgeschlossenen Scan samt Daten (Seiten, Befunde, Test-Aufzeichnungen) löschen. */
  const deleteJob = async (id) => {
    return await $fetch(`${base}/jobs/${id}`, { method: 'DELETE' })
  }

  const getResults = async (id) => {
    return await $fetch(`${base}/jobs/${id}/results`)
  }

  const getTests = async () => {
    return await $fetch(`${base}/tests`)
  }

  const getTestsSummary = async () => {
    return await $fetch(`${base}/tests/summary`)
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
   * Events werden als ProgressEvent-JSON geliefert; onClose wird auch bei
   * Server-Close aufgerufen (Job fertig → erneutes Laden der Ergebnisse).
   */
  const connectWs = (jobId, { onEvent, onClose } = {}) => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/jobs/${jobId}`)
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
