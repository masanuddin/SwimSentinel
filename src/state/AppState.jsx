import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { primeAudio, startBuzzer, stopBuzzer } from '../audio/buzzer'

/**
 * Shared state seluruh app (in-memory, tanpa backend/storage).
 * Simulasi MENULIS lewat actions; Map & Report MEMBACA dari sini.
 * Tipe: lihat src/state/types.js
 *
 * Mesin urutan tenggelam (timer) sengaja hidup DI SINI, bukan di halaman
 * Simulasi — supaya urutan tetap berjalan & buzzer tetap bunyi walau user
 * pindah tab ke Map/Report di tengah skenario.
 */

/** Durasi fase meronta sebelum terdeteksi diam (mirror: gyro variance tinggi). */
export const STRUGGLE_SEC = 2
/** Ambang submersi sebelum ALARM (mirror: konfirmasi kamera bawah air). */
export const CONFIRM_SEC = 6

const AppStateContext = createContext(null)

/** @type {import('./types').Zone[]} */
const seedZones = [1, 2, 3, 4].map((id) => ({
  id,
  label: `Zona ${id}`,
  riskCount: 0,
}))

/** Posisi deck default untuk perenang ke-n (1-based). */
const deckPos = (n) => ({ x: 9, y: 18 + (n - 1) * 14 })

/** @type {import('./types').Swimmer[]} */
const seedSwimmers = [
  { id: 'BR-01', name: 'Perenang 1', zoneId: null, status: 'idle', submersionSec: 0, battery: 92, pos: deckPos(1) },
  { id: 'BR-02', name: 'Perenang 2', zoneId: null, status: 'idle', submersionSec: 0, battery: 78, pos: deckPos(2) },
]

const HOUR = 60 * 60 * 1000

/** Alarm lampau (resolved) biar Report punya data sejak awal. */
/** @type {import('./types').Alarm[]} */
const seedAlarms = [
  { id: 'AL-001', timestamp: Date.now() - 26 * HOUR, zoneId: 3, swimmerId: 'BR-07', responseSec: 14, resolved: true },
  { id: 'AL-002', timestamp: Date.now() - 8 * HOUR, zoneId: 1, swimmerId: 'BR-04', responseSec: 9, resolved: true },
  { id: 'AL-003', timestamp: Date.now() - 5 * HOUR, zoneId: 3, swimmerId: 'BR-11', responseSec: 21, resolved: true },
  { id: 'AL-004', timestamp: Date.now() - 2 * HOUR, zoneId: 2, swimmerId: 'BR-02', responseSec: 12, resolved: true },
]

let alarmSeq = seedAlarms.length

export function AppStateProvider({ children }) {
  const [zones, setZones] = useState(seedZones)
  const [swimmers, setSwimmers] = useState(seedSwimmers)
  const [alarms, setAlarms] = useState(seedAlarms)
  const [muted, setMuted] = useState(false)

  // Mirror swimmers untuk dibaca dari dalam timer (hindari closure basi)
  const swimmersRef = useRef(swimmers)
  useEffect(() => {
    swimmersRef.current = swimmers
  }, [swimmers])

  // Timer per perenang: { struggle: timeout, tick: interval, recover: timeout }
  const timersRef = useRef({})
  const clearTimers = useCallback((id) => {
    const tm = timersRef.current[id]
    if (!tm) return
    if (tm.struggle) clearTimeout(tm.struggle)
    if (tm.tick) clearInterval(tm.tick)
    if (tm.recover) clearTimeout(tm.recover)
    delete timersRef.current[id]
  }, [])

  /** Tambah alarm baru; zona terkait naik riskCount. */
  const addAlarm = useCallback(({ zoneId, swimmerId }) => {
    alarmSeq += 1
    const alarm = {
      id: `AL-${String(alarmSeq).padStart(3, '0')}`,
      timestamp: Date.now(),
      zoneId,
      swimmerId,
      resolved: false,
    }
    setAlarms((prev) => [...prev, alarm])
    setZones((prev) =>
      prev.map((z) => (z.id === zoneId ? { ...z, riskCount: z.riskCount + 1 } : z)),
    )
    return alarm
  }, [])

  /** Patch sebagian field swimmer, mis. updateSwimmer('BR-01', { pos }) */
  const updateSwimmer = useCallback((id, patch) => {
    setSwimmers((prev) => prev.map((s) => (s.id === id ? { ...s, ...patch } : s)))
  }, [])

  /** Tandai alarm selesai + catat waktu respons (detik). */
  const resolveAlarm = useCallback((id, responseSec) => {
    setAlarms((prev) =>
      prev.map((a) => (a.id === id ? { ...a, resolved: true, responseSec } : a)),
    )
  }, [])

  /**
   * Picu urutan tenggelam pada perenang yang sedang berenang:
   * Meronta (STRUGGLE_SEC) → Terdeteksi diam (submersionSec naik tiap
   * detik) → saat mencapai CONFIRM_SEC tanpa diselamatkan → ALARM.
   * submersionSec terus berjalan setelah alarm (timer di Map).
   */
  const triggerDrowning = useCallback(
    (id) => {
      primeAudio() // dipanggil dari klik user → izin audio aman
      const sw = swimmersRef.current.find((s) => s.id === id)
      if (!sw || sw.status !== 'swimming' || sw.zoneId == null) return

      clearTimers(id)
      updateSwimmer(id, { status: 'struggling', submersionSec: 0 })

      const struggle = setTimeout(() => {
        updateSwimmer(id, { status: 'drowning', submersionSec: 0 })
        let sec = 0
        const tick = setInterval(() => {
          sec += 1
          updateSwimmer(id, { submersionSec: sec })
          if (sec === CONFIRM_SEC) {
            const cur = swimmersRef.current.find((s) => s.id === id)
            addAlarm({ zoneId: cur?.zoneId ?? 0, swimmerId: id })
          }
        }, 1000)
        timersRef.current[id] = { ...timersRef.current[id], tick }
      }, STRUGGLE_SEC * 1000)

      timersRef.current[id] = { struggle }
    },
    [addAlarm, clearTimers, updateSwimmer],
  )

  /**
   * Selamatkan perenang: hentikan urutan, resolve alarm yang terbuka
   * (catat responseSec), status "rescued" sebentar lalu kembali berenang.
   */
  const rescueSwimmer = useCallback(
    (id) => {
      clearTimers(id)
      setAlarms((prev) =>
        prev.map((a) =>
          !a.resolved && a.swimmerId === id
            ? {
                ...a,
                resolved: true,
                responseSec: Math.max(1, Math.round((Date.now() - a.timestamp) / 1000)),
              }
            : a,
        ),
      )
      updateSwimmer(id, { status: 'rescued', submersionSec: 0 })
      const recover = setTimeout(() => {
        setSwimmers((prev) =>
          prev.map((s) =>
            s.id === id && s.status === 'rescued' ? { ...s, status: 'swimming' } : s,
          ),
        )
      }, 3000)
      timersRef.current[id] = { recover }
    },
    [clearTimers, updateSwimmer],
  )

  /** Tambah perenang baru di deck (maks 6). */
  const addSwimmer = useCallback(() => {
    setSwimmers((prev) => {
      if (prev.length >= 6) return prev
      const n = prev.length + 1
      return [
        ...prev,
        {
          id: `BR-${String(n).padStart(2, '0')}`,
          name: `Perenang ${n}`,
          zoneId: null,
          status: 'idle',
          submersionSec: 0,
          battery: 60 + Math.round(Math.random() * 40),
          pos: deckPos(n),
        },
      ]
    })
  }, [])

  const toggleMute = useCallback(() => setMuted((m) => !m), [])

  // Buzzer global: bunyi selama ada alarm belum resolved & tidak di-mute
  const hasActiveAlarm = alarms.some((a) => !a.resolved)
  useEffect(() => {
    if (hasActiveAlarm && !muted) startBuzzer()
    else stopBuzzer()
  }, [hasActiveAlarm, muted])

  // Bersih-bersih saat provider unmount
  useEffect(() => {
    const timers = timersRef.current
    return () => {
      Object.keys(timers).forEach((id) => {
        const tm = timers[id]
        if (tm.struggle) clearTimeout(tm.struggle)
        if (tm.tick) clearInterval(tm.tick)
        if (tm.recover) clearTimeout(tm.recover)
      })
      stopBuzzer()
    }
  }, [])

  const value = useMemo(
    () => ({
      zones,
      swimmers,
      alarms,
      muted,
      hasActiveAlarm,
      addAlarm,
      updateSwimmer,
      resolveAlarm,
      triggerDrowning,
      rescueSwimmer,
      addSwimmer,
      toggleMute,
    }),
    [
      zones,
      swimmers,
      alarms,
      muted,
      hasActiveAlarm,
      addAlarm,
      updateSwimmer,
      resolveAlarm,
      triggerDrowning,
      rescueSwimmer,
      addSwimmer,
      toggleMute,
    ],
  )

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>
}

export function useAppState() {
  const ctx = useContext(AppStateContext)
  if (!ctx) throw new Error('useAppState harus dipakai di dalam <AppStateProvider>')
  return ctx
}
