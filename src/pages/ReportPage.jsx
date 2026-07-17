import { useLang } from '../i18n/LangContext'
import { useAppState } from '../state/AppState'
import { Panel } from '../components/ui/Panel'
import { StatusPill } from '../components/ui/StatusPill'
import { StatTile } from '../components/ui/StatTile'
import { ZONE_RECTS } from '../lib/pool'
import { fmt } from '../lib/fmt'

/**
 * M4 Report: tabel alarm hari ini, grafik bulanan, statistik respons,
 * heatmap zona rawan, rekomendasi personil. Membaca shared state —
 * alarm baru dari Simulasi langsung masuk sini.
 */

const isSameDay = (ts, ref = new Date()) => {
  const d = new Date(ts)
  return (
    d.getDate() === ref.getDate() &&
    d.getMonth() === ref.getMonth() &&
    d.getFullYear() === ref.getFullYear()
  )
}

/** 6 bulan terakhir (termasuk bulan ini): [{ key, label, count }] */
function monthlyCounts(alarms, locale) {
  const now = new Date()
  return Array.from({ length: 6 }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - (5 - i), 1)
    const count = alarms.filter((a) => {
      const t = new Date(a.timestamp)
      return t.getFullYear() === d.getFullYear() && t.getMonth() === d.getMonth()
    }).length
    return {
      key: `${d.getFullYear()}-${d.getMonth()}`,
      label: d.toLocaleDateString(locale, { month: 'short' }),
      count,
    }
  })
}

function MonthlyChart({ months, R }) {
  const max = Math.max(1, ...months.map((m) => m.count))
  return (
    <div>
      <div className="flex h-40 items-end gap-2 md:gap-3">
        {months.map((m) => (
          <div
            key={m.key}
            className="group flex h-full flex-1 flex-col items-center justify-end gap-1"
            title={`${m.label}: ${m.count} ${R.alarmsUnit}`}
          >
            <span className="num text-xs font-semibold text-muted transition-colors group-hover:text-text">
              {m.count}
            </span>
            <div
              className="w-full max-w-12 rounded-t-[4px] bg-accent/80 transition-colors group-hover:bg-accent"
              style={{ height: m.count === 0 ? '2px' : `${(m.count / max) * 82}%` }}
            />
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex gap-2 border-t border-border pt-1.5 md:gap-3">
        {months.map((m) => (
          <span key={m.key} className="flex-1 text-center text-xs text-muted">
            {m.label}
          </span>
        ))}
      </div>
    </div>
  )
}

function ZoneHeatmap({ zoneCounts, t, R }) {
  const max = Math.max(1, ...zoneCounts.map((z) => z.count))
  return (
    <div>
      <div className="relative mx-auto aspect-[16/10] w-full max-w-md overflow-hidden rounded-md border border-border bg-bg">
        {ZONE_RECTS.map((z) => {
          const { count } = zoneCounts.find((c) => c.id === z.id)
          // Sequential satu hue (merah): muda → pekat menurut jumlah alarm
          const alpha = 0.08 + (count / max) * 0.5
          return (
            <div
              key={z.id}
              className="absolute flex flex-col items-center justify-center border border-border"
              style={{
                left: `${z.x1}%`,
                top: `${z.y1}%`,
                width: `${z.x2 - z.x1}%`,
                height: `${z.y2 - z.y1}%`,
                backgroundColor: `rgba(239, 68, 68, ${alpha})`,
              }}
              title={`${t.zone} ${z.id}: ${count} ${R.alarmsUnit}`}
            >
              <span className="text-xs font-semibold text-muted">
                {t.zone} {z.id}
              </span>
              <span className="num text-xl font-bold text-text">{count}</span>
              <span className="text-[10px] text-muted">{R.alarmsUnit}</span>
            </div>
          )
        })}
      </div>
      <div className="mx-auto mt-3 flex max-w-md items-center gap-2 text-[10px] uppercase tracking-wider text-muted">
        <span>{R.heatLow}</span>
        <div
          className="h-1.5 flex-1 rounded-full"
          style={{
            background:
              'linear-gradient(90deg, rgba(239,68,68,0.08), rgba(239,68,68,0.58))',
          }}
        />
        <span>{R.heatHigh}</span>
      </div>
    </div>
  )
}

function TodayTable({ todayAlarms, t, R, locale }) {
  if (todayAlarms.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted">{R.todayEmpty}</p>
    )
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs uppercase tracking-wider text-muted">
            <th className="py-2 pr-4 font-semibold">{R.table.time}</th>
            <th className="py-2 pr-4 font-semibold">{R.table.alarm}</th>
            <th className="py-2 pr-4 font-semibold">{R.table.band}</th>
            <th className="py-2 pr-4 font-semibold">{R.table.zone}</th>
            <th className="py-2 pr-4 font-semibold">{R.table.response}</th>
            <th className="py-2 font-semibold">{R.table.status}</th>
          </tr>
        </thead>
        <tbody>
          {todayAlarms.map((a) => (
            <tr key={a.id} className="border-b border-border last:border-0">
              <td className="num py-2.5 pr-4">
                {new Date(a.timestamp).toLocaleTimeString(locale, {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </td>
              <td className="num py-2.5 pr-4 text-muted">{a.id}</td>
              <td className="num py-2.5 pr-4">{a.swimmerId}</td>
              <td className="py-2.5 pr-4">
                {t.zone} {a.zoneId}
              </td>
              <td className="num py-2.5 pr-4">
                {a.responseSec != null ? `${a.responseSec}${t.sim.sec}` : '—'}
              </td>
              <td className="py-2.5">
                {a.resolved ? (
                  <StatusPill level="safe" label={R.statusDone} />
                ) : (
                  <StatusPill level="danger" label={R.statusActive} />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function ReportPage() {
  const { t, lang } = useLang()
  const R = t.report
  const locale = lang === 'id' ? 'id-ID' : 'en-US'
  const { alarms } = useAppState()

  const todayAlarms = alarms
    .filter((a) => isSameDay(a.timestamp))
    .sort((a, b) => b.timestamp - a.timestamp)

  const months = monthlyCounts(alarms, locale)

  const zoneCounts = [1, 2, 3, 4].map((id) => ({
    id,
    count: alarms.filter((a) => a.zoneId === id).length,
  }))
  const topZone = zoneCounts.reduce((a, b) => (b.count > a.count ? b : a))

  const responseTimes = alarms
    .filter((a) => a.resolved && a.responseSec != null)
    .map((a) => a.responseSec)
  const avgResponse =
    responseTimes.length > 0
      ? Math.round(responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length)
      : 0
  const fastest = responseTimes.length > 0 ? Math.min(...responseTimes) : 0

  const recommendations = []
  if (topZone.count > 0) {
    recommendations.push(
      fmt(R.recStaff, {
        zone: `${t.zone} ${topZone.id}`,
        count: topZone.count,
        pct: Math.round((topZone.count / Math.max(1, alarms.length)) * 100),
      }),
    )
  }
  recommendations.push(
    fmt(avgResponse > 15 ? R.recResponseSlow : R.recResponseGood, {
      avg: avgResponse,
    }),
  )

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-bold tracking-wide">
          {t.pageTitles.report}
        </h1>
        <p className="mt-1 text-sm text-muted">{R.subtitle}</p>
      </header>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile value={todayAlarms.length} label={R.tiles.today} />
        <StatTile value={alarms.length} label={R.tiles.total} />
        <StatTile value={avgResponse} suffix={t.sim.sec} label={R.tiles.avgResponse} />
        <StatTile value={fastest} suffix={t.sim.sec} label={R.tiles.fastest} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={R.monthlyPanel}>
          <MonthlyChart months={months} R={R} />
        </Panel>
        <Panel title={R.heatmapPanel}>
          <ZoneHeatmap zoneCounts={zoneCounts} t={t} R={R} />
        </Panel>
      </div>

      <Panel title={R.todayPanel}>
        <TodayTable todayAlarms={todayAlarms} t={t} R={R} locale={locale} />
      </Panel>

      <Panel title={R.recPanel}>
        <ul className="space-y-2">
          {recommendations.map((rec) => (
            <li
              key={rec}
              className="flex items-start gap-2.5 text-sm leading-relaxed text-text"
            >
              <span className="mt-0.5">💡</span>
              {rec}
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  )
}
