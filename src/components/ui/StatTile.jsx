/**
 * StatTile angka besar + label kecil, gaya ops dashboard.
 * danger: tile ikut berkedip merah saat value > 0 (mis. jumlah alarm aktif).
 * suffix: satuan kecil di belakang angka (mis. " dtk").
 */
export function StatTile({ value, label, suffix = '', danger = false }) {
  return (
    <div
      className={`rounded-md border px-4 py-3 ${
        danger && value > 0 ? 'alarm-blink border-danger' : 'border-border bg-panel'
      }`}
    >
      <div className="num text-2xl font-bold">
        {value}
        {suffix && <span className="text-sm font-semibold text-muted">{suffix}</span>}
      </div>
      <div className="mt-0.5 text-xs font-medium uppercase tracking-wider text-muted">
        {label}
      </div>
    </div>
  )
}
