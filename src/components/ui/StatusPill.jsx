import { useLang } from '../../i18n/LangContext'

const styles = {
  safe: 'text-safe border-safe/40 bg-safe/10',
  warn: 'text-warn border-warn/40 bg-warn/10',
  danger: 'text-danger border-danger/40 bg-danger/10',
}

const dotStyles = {
  safe: 'bg-safe',
  warn: 'bg-warn',
  danger: 'bg-danger',
}

/**
 * StatusPill — badge status keselamatan.
 * level: 'safe' | 'warn' | 'danger'
 * label opsional; default pakai kamus i18n (Aman/Waspada/Bahaya).
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
