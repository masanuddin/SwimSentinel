/**
 * ShinyText teks gradient dengan kilau putih yang menyapu terus-menerus
 * dari kiri ke kanan (CSS keyframes, tanpa framer-motion).
 * Warna dasar #64CEFB, kilau #FFFFFF, durasi 3 dtk, sudut 100°.
 * Styling: lihat .shiny-text di src/index.css
 */
export function ShinyText({ children, className = '' }) {
  return <span className={`shiny-text ${className}`}>{children}</span>
}
