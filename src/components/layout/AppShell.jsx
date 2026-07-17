import { useLang } from '../../i18n/LangContext'
import { useAppState } from '../../state/AppState'
import { IconButton } from '../ui/Button'
import { SegmentedToggle } from '../ui/Toggle'
import { WavesIcon, VolumeIcon, VolumeMutedIcon } from '../ui/Icons'

/** ID tab navigasi — dipakai App.jsx sebagai "route". */
export const NAV_IDS = ['landing', 'map', 'simulation', 'report']

function Brand() {
  const { t } = useLang()
  return (
    <div className="flex items-center gap-2.5 md:gap-3">
      <div className="flex h-8 w-8 items-center justify-center rounded-md border border-accent/50 bg-accent/15 text-accent md:h-9 md:w-9">
        <WavesIcon className="h-4 w-4 md:h-5 md:w-5" />
      </div>
      <div className="leading-tight">
        <div className="text-sm font-bold tracking-wide md:text-base">
          {t.appName}
        </div>
        <div className="hidden text-[11px] font-medium uppercase tracking-widest text-muted sm:block">
          {t.appTagline}
        </div>
      </div>
    </div>
  )
}

function NavTabs({ page, onNavigate }) {
  const { t } = useLang()
  return (
    <nav
      className="flex items-center gap-1 whitespace-nowrap"
      aria-label="Navigasi utama"
    >
      {NAV_IDS.map((id) => {
        const active = page === id
        return (
          <button
            key={id}
            type="button"
            aria-current={active ? 'page' : undefined}
            onClick={() => onNavigate(id)}
            className={`rounded-md border px-3.5 py-2 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
              active
                ? 'border-accent/60 bg-accent/15 text-text'
                : 'border-transparent text-muted hover:bg-panel hover:text-text'
            }`}
          >
            {t.nav[id]}
          </button>
        )
      })}
    </nav>
  )
}

function Topbar({ page, onNavigate }) {
  const { lang, setLang, t } = useLang()
  const { muted, toggleMute } = useAppState()

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-bg/95 backdrop-blur">
      <div className="mx-auto max-w-[1600px] px-4 md:px-6">
        <div className="flex h-14 items-center justify-between gap-3 md:h-16">
          <Brand />
          {/* Nav inline hanya di layar besar */}
          <div className="hidden lg:block">
            <NavTabs page={page} onNavigate={onNavigate} />
          </div>
          <div className="flex items-center gap-2 md:gap-2.5">
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
          </div>
        </div>
        {/* Nav baris kedua di mobile/tablet: scroll horizontal kalau sempit */}
        <div className="overflow-x-auto pb-2 lg:hidden">
          <NavTabs page={page} onNavigate={onNavigate} />
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
            : 'mx-auto w-full max-w-[1600px] flex-1 px-4 py-4 md:px-6 md:py-6'
        }
      >
        {children}
      </main>
    </div>
  )
}
