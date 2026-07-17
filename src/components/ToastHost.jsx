import { useCallback, useEffect, useRef, useState } from 'react'
import { useLang } from '../i18n/LangContext'
import { useAppState } from '../state/AppState'
import { fmt } from '../lib/fmt'

/**
 * M5 — Toast notifikasi global. Mengamati shared state (bukan dipanggil
 * manual): meronta terdeteksi (warn), alarm menyala (danger, ada tombol
 * "Lihat Map"), alarm ditanggapi (safe). Auto-hilang 6 dtk, bisa ditutup.
 */

const KIND_CLS = {
  safe: 'border-safe/60',
  warn: 'border-warn/60',
  danger: 'border-danger alarm-blink',
}

export function ToastHost({ onNavigate }) {
  const { t } = useLang()
  const { alarms, swimmers } = useAppState()
  const [toasts, setToasts] = useState([])
  const prevAlarmsRef = useRef(alarms)
  const prevSwimmersRef = useRef(swimmers)
  const seqRef = useRef(0)

  const dismiss = useCallback((id) => {
    setToasts((ts) => ts.filter((x) => x.id !== id))
  }, [])

  const push = useCallback((toast) => {
    seqRef.current += 1
    const id = seqRef.current
    setToasts((ts) => [...ts, { id, ...toast }].slice(-4))
    setTimeout(() => dismiss(id), 6000)
  }, [dismiss])

  // Alarm baru menyala / alarm ditanggapi
  useEffect(() => {
    const prev = prevAlarmsRef.current
    prevAlarmsRef.current = alarms
    alarms.forEach((a) => {
      const old = prev.find((p) => p.id === a.id)
      if (!old && !a.resolved) {
        push({
          kind: 'danger',
          icon: '🚨',
          text: fmt(t.toast.alarm, { zone: `${t.zone} ${a.zoneId}`, id: a.swimmerId }),
          action: 'map',
        })
      } else if (old && !old.resolved && a.resolved) {
        push({
          kind: 'safe',
          icon: '✅',
          text: fmt(t.toast.resolved, { id: a.swimmerId, sec: a.responseSec }),
        })
      }
    })
  }, [alarms, push, t])

  // Fase meronta terdeteksi (mirror: paket "MERONTA!" dari gelang)
  useEffect(() => {
    const prev = prevSwimmersRef.current
    prevSwimmersRef.current = swimmers
    swimmers.forEach((s) => {
      const old = prev.find((p) => p.id === s.id)
      if (old && old.status !== 'struggling' && s.status === 'struggling') {
        push({
          kind: 'warn',
          icon: '⚠️',
          text: fmt(t.toast.struggling, { id: s.id, zone: `${t.zone} ${s.zoneId}` }),
        })
      }
    })
  }, [swimmers, push, t])

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-[60] flex w-[calc(100vw-2rem)] flex-col gap-2 sm:w-80">
      {toasts.map(({ id, kind, icon, text, action }) => (
        <div
          key={id}
          role="status"
          className={`toast-in flex items-center gap-2.5 rounded-md border bg-panel/95 px-3.5 py-2.5 text-sm font-semibold shadow-lg backdrop-blur ${KIND_CLS[kind]}`}
        >
          <span>{icon}</span>
          <span className="min-w-0 flex-1">{text}</span>
          {action === 'map' && (
            <button
              type="button"
              onClick={() => {
                onNavigate('map')
                dismiss(id)
              }}
              className="shrink-0 rounded border border-border px-2 py-1 text-xs text-muted transition-colors hover:border-accent/60 hover:text-text"
            >
              {t.toast.openMap}
            </button>
          )}
          <button
            type="button"
            aria-label="✕"
            onClick={() => dismiss(id)}
            className="shrink-0 text-muted transition-colors hover:text-text"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
