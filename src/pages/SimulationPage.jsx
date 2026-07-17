import { useRef } from 'react'
import { useLang } from '../i18n/LangContext'
import { useAppState, CONFIRM_SEC } from '../state/AppState'
import { Panel } from '../components/ui/Panel'
import { Button } from '../components/ui/Button'
import { StatusPill } from '../components/ui/StatusPill'
import {
  POOL_RECT,
  ZONE_RECTS,
  ZONE_CLS,
  zoneFromPos,
  zoneVisualState,
} from '../lib/pool'

/**
 * M2 — Simulasi (jantung demo).
 * Mekanik: DRAG = pindahkan posisi (deck ↔ zona), KLIK = picu tenggelam.
 * Urutan & buzzer dijalankan mesin di AppState — tetap hidup saat pindah tab.
 */

const STATUS_LEVEL = {
  idle: 'muted',
  swimming: 'safe',
  struggling: 'warn',
  drowning: 'danger',
  rescued: 'safe',
}

const STATUS_EMOJI = {
  idle: '🧍',
  swimming: '🏊',
  struggling: '😱',
  drowning: '🖐',
  rescued: '🛟',
}

const STATUS_ANIM = {
  swimming: 'anim-bob',
  struggling: 'anim-shake',
  drowning: 'anim-sink',
}

const RING_CLS = {
  muted: 'border-border bg-panel',
  safe: 'border-safe bg-safe/20',
  warn: 'border-warn bg-warn/20',
  danger: 'border-danger bg-danger/25',
}

const CHIP_CLS = {
  muted: 'text-muted',
  safe: 'text-safe',
  warn: 'text-warn',
  danger: 'text-danger',
}

const DRAGGABLE_STATUSES = ['idle', 'swimming', 'rescued']

const clamp = (v, min, max) => Math.min(max, Math.max(min, v))

function SwimmerToken({ s, alarmed, S, onPointerDown, onPointerMove, onPointerUp }) {
  const draggable = DRAGGABLE_STATUSES.includes(s.status)
  const level = alarmed ? 'danger' : STATUS_LEVEL[s.status]
  const label = alarmed ? S.alarm : S.swimmerStatus[s.status]
  const countdown =
    s.status === 'drowning' && !alarmed
      ? Math.max(0, CONFIRM_SEC - s.submersionSec)
      : null

  return (
    <div
      className={`absolute z-10 flex -translate-x-1/2 -translate-y-1/2 select-none flex-col items-center ${
        draggable ? 'cursor-grab touch-none active:cursor-grabbing' : ''
      }`}
      style={{ left: `${s.pos.x}%`, top: `${s.pos.y}%` }}
      onPointerDown={(e) => onPointerDown(e, s)}
      onPointerMove={onPointerMove}
      onPointerUp={(e) => onPointerUp(e, s)}
    >
      <div
        className={`flex h-10 w-10 items-center justify-center rounded-full border-2 text-xl md:h-11 md:w-11 md:text-2xl ${
          RING_CLS[level]
        } ${STATUS_ANIM[s.status] ?? ''} ${alarmed ? 'alarm-blink' : ''}`}
      >
        {STATUS_EMOJI[s.status]}
      </div>
      <div
        className={`num mt-1 whitespace-nowrap rounded border border-border bg-bg/85 px-1.5 py-0.5 text-[10px] font-semibold leading-tight ${CHIP_CLS[level]}`}
      >
        {s.id} · {label}
        {countdown != null && ` · ${countdown}`}
        {alarmed && ` · ${s.submersionSec}${S.sec}`}
      </div>
    </div>
  )
}

function PoolView({ swimmers, activeAlarms, S, t, areaRef, handlers }) {
  return (
    <div
      ref={areaRef}
      className="relative aspect-[4/3] w-full overflow-hidden rounded-md border border-border bg-bg sm:aspect-[16/10]"
    >
      {/* Label deck (area di luar kolam) */}
      <span className="absolute left-1 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] font-bold tracking-[0.3em] text-muted md:left-2">
        {S.deck}
      </span>

      {/* Zona kolam */}
      {ZONE_RECTS.map((z) => (
        <div
          key={z.id}
          className={`absolute border ${ZONE_CLS[zoneVisualState(z.id, swimmers, activeAlarms)]}`}
          style={{
            left: `${z.x1}%`,
            top: `${z.y1}%`,
            width: `${z.x2 - z.x1}%`,
            height: `${z.y2 - z.y1}%`,
          }}
        >
          <span className="absolute left-1.5 top-1 text-[10px] font-semibold uppercase tracking-wider text-muted md:left-2">
            {t.zone} {z.id}
          </span>
        </div>
      ))}

      {/* Garis tepi kolam */}
      <div
        className="pointer-events-none absolute rounded-sm border-2 border-accent/50"
        style={{
          left: `${POOL_RECT.x1}%`,
          top: `${POOL_RECT.y1}%`,
          width: `${POOL_RECT.x2 - POOL_RECT.x1}%`,
          height: `${POOL_RECT.y2 - POOL_RECT.y1}%`,
        }}
      />

      {/* Karakter perenang */}
      {swimmers.map((s) => (
        <SwimmerToken
          key={s.id}
          s={s}
          alarmed={activeAlarms.some((a) => a.swimmerId === s.id)}
          S={S}
          onPointerDown={handlers.down}
          onPointerMove={handlers.move}
          onPointerUp={handlers.up}
        />
      ))}
    </div>
  )
}

function AlarmBanner({ alarm, swimmers, S, t, onRescue }) {
  const sw = swimmers.find((s) => s.id === alarm.swimmerId)
  return (
    <div className="alarm-blink flex flex-wrap items-center justify-between gap-3 rounded-md border border-danger px-4 py-3">
      <div className="flex items-center gap-2.5 text-sm font-bold text-text">
        <span className="text-base">🚨</span>
        {S.alarm} — {t.zone} {alarm.zoneId} — {alarm.swimmerId}
        {sw && (
          <span className="num font-semibold text-danger">
            {S.submersion} {sw.submersionSec}
            {S.sec}
          </span>
        )}
      </div>
      <Button variant="danger" onClick={() => onRescue(alarm.swimmerId)}>
        {S.rescue}
      </Button>
    </div>
  )
}

function SwimmerList({ swimmers, activeAlarms, S, t, onTrigger, onRescue }) {
  return (
    <div>
      {swimmers.map((s) => {
        const alarmed = activeAlarms.some((a) => a.swimmerId === s.id)
        const level = alarmed ? 'danger' : STATUS_LEVEL[s.status]
        return (
          <div
            key={s.id}
            className="flex items-center justify-between gap-2 border-b border-border py-2.5 first:pt-0 last:border-0 last:pb-0"
          >
            <div className="min-w-0">
              <div className="text-sm font-semibold">
                {STATUS_EMOJI[s.status]} {s.id}
              </div>
              <div className="num mt-0.5 text-xs text-muted">
                {s.zoneId ? `${t.zone} ${s.zoneId}` : S.swimmerStatus.idle} · 🔋
                {s.battery}%
                {s.status === 'drowning' &&
                  ` · ${S.submersion} ${s.submersionSec}${S.sec}`}
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <StatusPill
                level={level}
                label={alarmed ? S.alarm : S.swimmerStatus[s.status]}
              />
              {s.status === 'swimming' && (
                <Button variant="ghost" onClick={() => onTrigger(s.id)}>
                  {S.trigger}
                </Button>
              )}
              {(s.status === 'struggling' || s.status === 'drowning') && (
                <Button variant="danger" onClick={() => onRescue(s.id)}>
                  {S.rescue}
                </Button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function SimulationPage() {
  const { t } = useLang()
  const S = t.sim
  const {
    swimmers,
    alarms,
    updateSwimmer,
    triggerDrowning,
    rescueSwimmer,
    addSwimmer,
  } = useAppState()

  const areaRef = useRef(null)
  const dragRef = useRef(null)

  const activeAlarms = alarms.filter((a) => !a.resolved)

  const handlers = {
    down: (e, s) => {
      if (!DRAGGABLE_STATUSES.includes(s.status)) return
      e.currentTarget.setPointerCapture(e.pointerId)
      dragRef.current = {
        id: s.id,
        sx: e.clientX,
        sy: e.clientY,
        moved: false,
        last: s.pos,
      }
    },
    move: (e) => {
      const d = dragRef.current
      if (!d) return
      if (!d.moved && Math.hypot(e.clientX - d.sx, e.clientY - d.sy) < 5) return
      d.moved = true
      const r = areaRef.current.getBoundingClientRect()
      const x = clamp(((e.clientX - r.left) / r.width) * 100, 2, 98)
      const y = clamp(((e.clientY - r.top) / r.height) * 100, 4, 96)
      d.last = { x, y }
      updateSwimmer(d.id, { pos: { x, y } })
    },
    up: (e, s) => {
      const d = dragRef.current
      dragRef.current = null
      if (!d || d.id !== s.id) return
      if (d.moved) {
        // Drop: posisi menentukan zona (null = deck)
        const zoneId = zoneFromPos(d.last.x, d.last.y)
        updateSwimmer(s.id, {
          zoneId,
          status: zoneId ? 'swimming' : 'idle',
          submersionSec: 0,
        })
      } else if (s.status === 'swimming' && s.zoneId != null) {
        // Klik (tanpa geser): picu urutan tenggelam
        triggerDrowning(s.id)
      }
    },
  }

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-bold tracking-wide">
          {t.pageTitles.simulation}
        </h1>
        <p className="mt-1 text-sm text-muted">{S.subtitle}</p>
      </header>

      {activeAlarms.map((a) => (
        <AlarmBanner
          key={a.id}
          alarm={a}
          swimmers={swimmers}
          S={S}
          t={t}
          onRescue={rescueSwimmer}
        />
      ))}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <Panel title={S.poolPanel}>
          <PoolView
            swimmers={swimmers}
            activeAlarms={activeAlarms}
            S={S}
            t={t}
            areaRef={areaRef}
            handlers={handlers}
          />
        </Panel>

        <div className="space-y-4">
          <Panel
            title={S.swimmersPanel}
            actions={
              <Button variant="ghost" onClick={addSwimmer}>
                {S.addSwimmer}
              </Button>
            }
          >
            <SwimmerList
              swimmers={swimmers}
              activeAlarms={activeAlarms}
              S={S}
              t={t}
              onTrigger={triggerDrowning}
              onRescue={rescueSwimmer}
            />
          </Panel>

          <Panel title={S.instructionsTitle}>
            <ol className="list-decimal space-y-2 pl-4 text-sm leading-relaxed text-muted">
              {S.instructions.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ol>
          </Panel>
        </div>
      </div>
    </div>
  )
}
