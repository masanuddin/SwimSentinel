/**
 * Klien SSE untuk cv-service (kamera + computer vision).
 *
 * Service-nya mengirim dua named event lewat `GET /events`:
 * - `heartbeat`       — tanda service hidup, cadence ~3 detik.
 * - `visual_evidence` — bukti visual satu track pada satu waktu.
 *
 * PENTING — `visual_evidence` boleh bernilai null di empat field:
 *   trackId, zoneId, rawClass, detectionConfidence
 * Contoh: `camera_unavailable` tidak punya track/zona; track di luar ROI
 * kolam punya `zoneId: null`. Konsumen WAJIB memperlakukan `zoneId: null`
 * sebagai "tidak berada di zona kolam" dan tidak boleh meng-eskalasinya
 * sebagai bukti di dalam kolam.
 *
 * trackId itu anonim dan sementara — bukan identitas orang, bukan pemilik
 * wristband. detectionConfidence itu skor object detection, BUKAN
 * probabilitas tenggelam.
 *
 * Bentuk payload visual_evidence:
 *   timestamp            string (ISO)
 *   cameraId             string
 *   trackId              number | null
 *   zoneId               1 | 2 | 3 | 4 | null
 *   rawClass             'normal_swimming' | 'distress_candidate' | 'out_of_water' | null
 *   detectionConfidence  number | null
 *   motionState          'normal' | 'low' | 'unknown'
 *   lowMotionDurationMs  number
 *   classPersistenceMs   number
 *   visibility           'clear' | 'limited' | 'lost' | 'unavailable'
 *   visualState          'normal' | 'watch' | 'suspected_distress'
 *                        | 'suspected_inactivity' | 'visibility_limited'
 *                        | 'track_lost' | 'camera_unavailable'
 *   evidence             string[]
 *   normalizedMovement   number | null
 */

const DEFAULT_CV_SERVICE_URL = 'http://127.0.0.1:8000'

/** Base URL cv-service, bisa diatur lewat VITE_CV_SERVICE_URL. */
export const CV_SERVICE_URL =
  import.meta.env.VITE_CV_SERVICE_URL ?? DEFAULT_CV_SERVICE_URL

/** Endpoint SSE hasil resolve dari base URL. */
export const CV_EVENTS_URL = `${CV_SERVICE_URL.replace(/\/$/, '')}/events`

/**
 * Sambung ke stream SSE cv-service.
 *
 * @param {(event: { type: 'heartbeat' | 'visual_evidence', data: any }) => void} onEvent
 * @param {string} [url]
 * @returns {() => void} fungsi untuk memutus koneksi
 */
export function connectCvEvents(onEvent, url = CV_EVENTS_URL) {
  const source = new EventSource(url)

  source.addEventListener('heartbeat', (event) => {
    onEvent({ type: 'heartbeat', data: JSON.parse(event.data) })
  })

  source.addEventListener('visual_evidence', (event) => {
    onEvent({ type: 'visual_evidence', data: JSON.parse(event.data) })
  })

  source.onerror = () => {
    // cv-service belum jalan itu kondisi normal saat dev — jangan berisik.
    if (
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1'
    ) {
      console.debug('CV SSE connection waiting or unavailable')
    }
  }

  return () => source.close()
}
