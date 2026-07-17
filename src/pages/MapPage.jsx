import { useEffect, useState } from 'react'
import { useLang } from '../i18n/LangContext'
import { useAppState } from '../state/AppState'
import { Panel } from '../components/ui/Panel'
import { Button } from '../components/ui/Button'
import { StatusPill } from '../components/ui/StatusPill'
import { StatTile } from '../components/ui/StatTile'
import {
  POOL_RECT,
  ZONE_RECTS,
  ZONE_CLS,
  zoneVisualState,
} from '../lib/pool'

/**
 * M3 — Map (pos lifeguard). Murni MEMBACA shared state:
 * status zona live, posisi perenang, kartu korban saat alarm + "Tanggapi".
 * Geometri kolam sama persis dengan Simulasi (src/lib/pool.js).
 */

const DOT_CLS = {
  idle: 'border-border bg-muted/60',
  swimming: 'border-safe bg-safe',
  struggling: 'border-warn bg-warn',
  drowning: 'border-danger bg-danger',
  rescued: 'border-safe bg-safe',
}

/** Status visual zona → level StatusPill (label default i18n Aman/Waspada/Bahaya) */
const ZONE_PILL_LEVEL = { alarm: 'danger', danger: 'danger', warn: 'warn', ok: 'safe' }

function SwimmerDot({ s, alarmed }) {
  return (
    <div
      className="absolute z-10 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center"
      style={{ left: `${s.pos.x}%`, top: `${s.pos.y}%` }}
    >
      {alarmed && (
        <span className="absolute -top-6 animate-bounce text-base">📍</span>
      )}
      <span className="relative flex h-3 w-3">
        {alarmed && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-danger opacity-70" />
        )}
        <span
          className={`relative inline-flex h-3 w-3 rounded-full border ${DOT_CLS[s.status]}`}
        />
      </span>
      <span
        className={`num mt-0.5 text-[9px] font-semibold ${
          alarmed ? 'text-danger' : 'text-muted'
        }`}
      >
        {s.id}
      </span>
    </div>
  )
}

function PoolMap({ swimmers, activeAlarms, t }) {
  return (
    <div className="relative aspect-[4/3] w-full overflow-hidden rounded-md border border-border bg-bg sm:aspect-[16/10]">
      <span className="absolute left-1 top-1/2 -translate-y-1/2 -rotate-90 text-[10px] font-bold tracking-[0.3em] text-muted md:left-2">
        {t.sim.deck}
      </span>

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

      <div
        className="pointer-events-none absolute rounded-sm border-2 border-accent/50"
        style={{
          left: `${POOL_RECT.x1}%`,
          top: `${POOL_RECT.y1}%`,
          width: `${POOL_RECT.x2 - POOL_RECT.x1}%`,
          height: `${POOL_RECT.y2 - POOL_RECT.y1}%`,
        }}
      />

      {swimmers.map((s) => (
        <SwimmerDot
          key={s.id}
          s={s}
          alarmed={activeAlarms.some((a) => a.swimmerId === s.id)}
        />
      ))}
    </div>
  )
}

function VictimCard({ alarm, swimmer, t, onRespond }) {
  const M = t.map
  const responseSec = Math.max(
    0,
    Math.round((Date.now() - alarm.timestamp) / 1000),
  )
  return (
    <div className="space-y-3 rounded-md border border-danger bg-danger/10 p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="text-sm font-bold">🚨 {alarm.swimmerId}</div>
        <StatusPill level="danger" label={t.sim.alarm} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <div className="num text-lg font-bold">{alarm.zoneId}</div>
          <div className="text-[10px] uppercase tracking-wider text-muted">
            {t.zone}
          </div>
        </div>
        <div>
          <div className="num text-lg font-bold text-danger">
            {swimmer ? `${swimmer.submersionSec}${t.sim.sec}` : '—'}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-muted">
            {t.sim.submersion}
          </div>
        </div>
        <div>
          <div className="num text-lg font-bold text-warn">
            {responseSec}
            {t.sim.sec}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-muted">
            {M.responseTime}
          </div>
        </div>
      </div>
      <Button
        variant="danger"
        className="w-full justify-center"
        onClick={() => onRespond(alarm.swimmerId)}
      >
        {M.respond}
      </Button>
    </div>
  )
}

function ZoneStatusList({ zones, swimmers, activeAlarms, t }) {
  const M = t.map
  return (
    <div>
      {zones.map((z) => {
        const state = zoneVisualState(z.id, swimmers, activeAlarms)
        const count = swimmers.filter((s) => s.zoneId === z.id).length
        return (
          <div
            key={z.id}
            className="flex items-center justify-between gap-2 border-b border-border py-2.5 first:pt-0 last:border-0 last:pb-0"
          >
            <div>
              <div className="text-sm font-semibold">
                {t.zone} {z.id}
              </div>
              <div className="num mt-0.5 text-xs text-muted">
                {count} {M.swimmersShort}
              </div>
            </div>
            <StatusPill level={ZONE_PILL_LEVEL[state]} />
          </div>
        )
      })}
    </div>
  )
}

export function MapPage() {
  const { t } = useLang()
  const M = t.map
  const { zones, swimmers, alarms, rescueSwimmer } = useAppState()

  const activeAlarms = alarms.filter((a) => !a.resolved)

  // Ticker 1 dtk agar timer respons di kartu korban berjalan live
  const [, setTick] = useState(0)
  useEffect(() => {
    if (activeAlarms.length === 0) return
    const iv = setInterval(() => setTick((n) => n + 1), 1000)
    return () => clearInterval(iv)
  }, [activeAlarms.length])

  const inWater = swimmers.filter((s) => s.zoneId != null).length
  const onDeck = swimmers.length - inWater

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-bold tracking-wide">{t.pageTitles.dashboard}</h1>
        <p className="mt-1 text-sm text-muted">{M.subtitle}</p>
      </header>

      <div className="grid grid-cols-3 gap-4">
        <StatTile value={inWater} label={M.stats.inWater} />
        <StatTile value={onDeck} label={M.stats.onDeck} />
        <StatTile value={activeAlarms.length} label={M.stats.activeAlarms} danger />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <Panel title={M.mapPanel}>
          <PoolMap swimmers={swimmers} activeAlarms={activeAlarms} t={t} />
        </Panel>

        <div className="space-y-4">
          <Panel title={M.alarmsPanel}>
            {activeAlarms.length === 0 ? (
              <div className="flex flex-col items-center gap-1.5 py-6 text-center">
                <span className="text-xl">✅</span>
                <div className="text-sm font-semibold text-safe">{M.noAlarm}</div>
                <div className="text-xs text-muted">{M.allSafe}</div>
              </div>
            ) : (
              <div className="space-y-3">
                {activeAlarms.map((a) => (
                  <VictimCard
                    key={a.id}
                    alarm={a}
                    swimmer={swimmers.find((s) => s.id === a.swimmerId)}
                    t={t}
                    onRespond={rescueSwimmer}
                  />
                ))}
              </div>
            )}
          </Panel>

          <Panel title={M.zonesPanel}>
            <ZoneStatusList
              zones={zones}
              swimmers={swimmers}
              activeAlarms={activeAlarms}
              t={t}
            />
          </Panel>
        </div>
      </div>
    </div>
  )
}
