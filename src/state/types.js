/**
 * Tipe data shared state (JSDoc). Sesuai CLAUDE.md §7.
 *
 * @typedef {'idle'|'swimming'|'struggling'|'drowning'|'rescued'} SwimmerStatus
 *
 * @typedef {Object} Swimmer
 * @property {string} id            - ID gelang, mis. "BR-01"
 * @property {string} [name]
 * @property {number|null} zoneId   - 1..4, null = di deck
 * @property {SwimmerStatus} status
 * @property {number} submersionSec - detik terendam (0 kalau tidak)
 * @property {number} battery       - persen baterai gelang 0..100
 * @property {{x:number,y:number}} pos - posisi di area simulasi (% 0..100),
 *                                    dipakai UI Simulasi (lihat src/lib/pool.js)
 *
 * @typedef {Object} Zone
 * @property {number} id            - 1..4
 * @property {string} label         - "Zona 1".."Zona 4"
 * @property {number} riskCount     - jumlah insiden historis (buat heatmap Report)
 *
 * @typedef {Object} Alarm
 * @property {string} id
 * @property {number} timestamp     - epoch ms
 * @property {number} zoneId
 * @property {string} swimmerId
 * @property {number} [responseSec] - waktu respons lifeguard (detik)
 * @property {boolean} resolved
 */

export {}
