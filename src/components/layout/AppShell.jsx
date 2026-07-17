import { useLang } from '../../i18n/LangContext'
import { useAppState } from '../../state/AppState'
import { IconButton } from '../ui/Button'
import { SegmentedToggle } from '../ui/Toggle'
import {
  HomeIcon,
  MapIcon,
  WavesIcon,
  ChartIcon,
  VolumeIcon,
  VolumeMutedIcon,
} from '../ui/Icons'

/** Definisi tab navigasi — id dipakai App.jsx sebagai "route". */
export const NAV_ITEMS = [
  { id: 'landing', Icon: HomeIcon },
  { id: 'map', Icon: MapIcon },
  { id: 'simulation', Icon: WavesIcon },
  { id: 'report', Icon: ChartIcon },
]

function Brand() {
  const { t } = useLang()
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-md border border-accent/50 bg-accent/15 text-accent">
        <WavesIcon className="h-5 w-5" />
      </div>
      <div className="leading-tight">
        <div className="text-base font-bold tracking-wide">{t.appName}</div>
        <div className="text-[11px] font-medium uppercase tracking-widest text-muted">
          {t.appTagline}
        </div>
      </div>
    </div>
  )
}

function NavTabs({ page, onNavigate }) {
  const { t } = useLang()
  return (
    <nav className="flex items-center gap-1" aria-label="Navigasi utama">
      {NAV_ITEMS.map(({ id, Icon }) => {
        const active = page === id
        return (
          <button
            key={id}
            type="button"
            aria-current={active ? 'page' : undefined}
            onClick={() => onNavigate(id)}
            className={`inline-flex items-center gap-2 rounded-md border px-3.5 py-2 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
              active
                ? 'border-accent/60 bg-accent/15 text-text'
                : 'border-transparent text-muted hover:bg-panel hover:text-text'
            }`}
          >
            <Icon className="h-4 w-4" />
            {t.nav[id]}
          </button>
        )
      })}
    </nav>
  )
}

function LiveIndicator() {
  const { t } = useLang()
  return (
    <div className="flex items-center gap-1.5 rounded-md border border-safe/40 bg-safe/10 px-2.5 py-1 text-xs font-bold tracking-widest text-safe">
      <span className="live-dot h-2 w-2 rounded-full bg-safe" />
      {t.live}
    </div>
  )
}

function Topbar({ page, onNavigate }) {
  const { lang, setLang, t } = useLang()
  const { muted, toggleMute } = useAppState()

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-bg/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between gap-6 px-6">
        <Brand />
        <NavTabs page={page} onNavigate={onNavigate} />
        <div className="flex items-center gap-2.5">
          <SegmentedToggle
            label="Bahasa / Language"
            value={lang}
            onChange={setLang}
            options={[
              { value: 'id', label: 'ID' },
              { value: 'en', label: 'EN' },
            ]}
          />
          <IconButton
            label={muted ? t.unmuteAlarm : t.muteAlarm}
            active={muted}
            onClick={toggleMute}
          >
            {muted ? (
              <VolumeMutedIcon className="h-4 w-4" />
            ) : (
              <VolumeIcon className="h-4 w-4" />
            )}
          </IconButton>
          <LiveIndicator />
        </div>
      </div>
    </header>
  )
}

/**
 * AppShell: topbar (brand + nav 4 tab + kontrol) dan area konten.
 * Halaman aktif ditentukan `page` (view-switching, tanpa router).
 * fullBleed: halaman mengatur lebar/padding sendiri (dipakai Landing
 * untuk hero video selebar layar).
 */
export function AppShell({ page, onNavigate, fullBleed = false, children }) {
  return (
    <div className="flex min-h-full flex-col bg-bg">
      <Topbar page={page} onNavigate={onNavigate} />
      <main
        className={
          fullBleed
            ? 'flex-1'
            : 'mx-auto w-full max-w-[1600px] flex-1 px-6 py-6'
        }
      >
        {children}
      </main>
    </div>
  )
}
