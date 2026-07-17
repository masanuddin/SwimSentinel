/**
 * Design tokens SwimSentinel — versi JS, mirror dari @theme di src/index.css.
 * Pakai ini kalau butuh nilai warna di luar className Tailwind
 * (SVG dinamis, canvas, chart, Web Audio UI, dsb).
 */
export const colors = {
  bg: '#0A1626',
  panel: '#122138',
  border: '#1E3350',
  accent: '#2D6CDF',
  safe: '#22C55E',
  warn: '#F5A623',
  danger: '#EF4444',
  text: '#E6EDF5',
  muted: '#8CA0B8',
}

/** Peta status → warna. Level dipakai StatusPill & (nanti) zona/alarm. */
export const statusColors = {
  safe: colors.safe,
  warn: colors.warn,
  danger: colors.danger,
}
