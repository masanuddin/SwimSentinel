import { useLang } from '../../i18n/LangContext'

const styles = {
  safe: 'text-safe border-safe/40 bg-safe/10',
  warn: 'text-warn border-warn/40 bg-warn/10',
  danger: 'text-danger border-danger/40 bg-danger/10',
  muted: 'text-muted border-border bg-panel',
}

const dotStyles = {
  safe: 'bg-safe',
  warn: 'bg-warn',
  danger: 'bg-danger',
  muted: 'bg-muted',
}

/**
 * StatusPill badge status keselamatan.
 * level: 'safe' | 'warn' | 'danger' | 'muted' (netral, mis. di deck)
 * label opsional; default pakai kamus i18n (Aman/Waspada/Bahaya) —
 * level 'muted' tidak punya default, selalu kasih label.
 */
export function StatusPill({ level = 'safe', label, className = '' }) {
  const { t } = useLang()
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${styles[level]} ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotStyles[level]}`} />
      {label ?? t.status[level]}
    </span>
  )
}
