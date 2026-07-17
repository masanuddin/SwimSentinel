/**
 * Geometri kolam tampak atas (koordinat % dari area simulasi).
 * Dipakai Simulasi (drag & deteksi zona) dan Map (render zona) supaya
 * layout kolam KONSISTEN di kedua halaman.
 *
 * Area di luar POOL_RECT = deck.
 * Zona: 1 kiri-atas · 2 kanan-atas · 3 kiri-bawah · 4 kanan-bawah.
 */
export const POOL_RECT = { x1: 20, y1: 10, x2: 96, y2: 90 }

const midX = (POOL_RECT.x1 + POOL_RECT.x2) / 2
const midY = (POOL_RECT.y1 + POOL_RECT.y2) / 2

export const ZONE_RECTS = [
  { id: 1, x1: POOL_RECT.x1, y1: POOL_RECT.y1, x2: midX, y2: midY },
  { id: 2, x1: midX, y1: POOL_RECT.y1, x2: POOL_RECT.x2, y2: midY },
  { id: 3, x1: POOL_RECT.x1, y1: midY, x2: midX, y2: POOL_RECT.y2 },
  { id: 4, x1: midX, y1: midY, x2: POOL_RECT.x2, y2: POOL_RECT.y2 },
]

/** Posisi (%,%) → id zona 1..4, atau null kalau di deck. */
export function zoneFromPos(x, y) {
  const z = ZONE_RECTS.find(
    (r) => x >= r.x1 && x <= r.x2 && y >= r.y1 && y <= r.y2,
  )
  return z ? z.id : null
}

/**
 * Status visual sebuah zona (dipakai Simulasi & Map biar konsisten):
 * 'alarm' (ada alarm aktif) > 'danger' (ada yang terdeteksi diam) >
 * 'warn' (ada yang meronta) > 'ok'.
 */
export function zoneVisualState(zoneId, swimmers, activeAlarms) {
  if (activeAlarms.some((a) => a.zoneId === zoneId)) return 'alarm'
  const inZone = swimmers.filter((s) => s.zoneId === zoneId)
  if (inZone.some((s) => s.status === 'drowning')) return 'danger'
  if (inZone.some((s) => s.status === 'struggling')) return 'warn'
  return 'ok'
}

/** Kelas Tailwind untuk kotak zona per status visual. */
export const ZONE_CLS = {
  alarm: 'alarm-blink border-danger/80',
  danger: 'border-danger/60 bg-danger/15',
  warn: 'border-warn/60 bg-warn/15',
  ok: 'border-accent/30 bg-accent/10',
}
