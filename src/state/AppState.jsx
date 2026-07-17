import { createContext, useCallback, useContext, useMemo, useState } from 'react'

/**
 * Shared state seluruh app (in-memory, tanpa backend/storage).
 * Simulasi MENULIS lewat actions; Map & Report MEMBACA dari sini.
 * Tipe: lihat src/state/types.js
 */

const AppStateContext = createContext(null)

/** @type {import('./types').Zone[]} */
const seedZones = [1, 2, 3, 4].map((id) => ({
  id,
  label: `Zona ${id}`,
  riskCount: 0,
}))

/** @type {import('./types').Swimmer[]} */
const seedSwimmers = [
  { id: 'BR-01', name: 'Perenang 1', zoneId: null, status: 'idle', submersionSec: 0, battery: 92 },
  { id: 'BR-02', name: 'Perenang 2', zoneId: null, status: 'idle', submersionSec: 0, battery: 78 },
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

  /** Patch sebagian field swimmer, mis. updateSwimmer('BR-01', { status: 'struggling' }) */
  const updateSwimmer = useCallback((id, patch) => {
    setSwimmers((prev) => prev.map((s) => (s.id === id ? { ...s, ...patch } : s)))
  }, [])

  /** Tandai alarm selesai + catat waktu respons (detik). */
  const resolveAlarm = useCallback((id, responseSec) => {
    setAlarms((prev) =>
      prev.map((a) => (a.id === id ? { ...a, resolved: true, responseSec } : a)),
    )
  }, [])

  const toggleMute = useCallback(() => setMuted((m) => !m), [])

  const value = useMemo(
    () => ({
      zones,
      swimmers,
      alarms,
      muted,
      addAlarm,
      updateSwimmer,
      resolveAlarm,
      toggleMute,
    }),
    [zones, swimmers, alarms, muted, addAlarm, updateSwimmer, resolveAlarm, toggleMute],
  )

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>
}

export function useAppState() {
  const ctx = useContext(AppStateContext)
  if (!ctx) throw new Error('useAppState harus dipakai di dalam <AppStateProvider>')
  return ctx
}
