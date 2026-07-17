import { useEffect, useRef, useState } from 'react'
import { useLang } from '../../i18n/LangContext'
import { useAppState } from '../../state/AppState'
import { IconButton } from '../ui/Button'
import { SegmentedToggle } from '../ui/Toggle'
import { WavesIcon, VolumeIcon, VolumeMutedIcon, UserIcon } from '../ui/Icons'

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
      aria-label={t.navLabel}
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

/**
 * ProfileMenu — avatar bulat + dropdown akun.
 * Belum login: Masuk/Login, Daftar/Register. Sudah login: Dashboard, Keluar.
 * Aksi Login/Register/Dashboard masih stub — di-wire saat integrasi Supabase.
 */
function ProfileMenu() {
  const { t } = useLang()
  const { user, setUser } = useAppState()
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false)
    }
    const onKeyDown = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const items = user
    ? [
        { key: 'dashboard', label: t.auth.dashboard, onClick: () => {} },
        { key: 'logout', label: t.auth.logout, onClick: () => setUser(null), danger: true },
      ]
    : [
        { key: 'login', label: t.auth.login, onClick: () => {} },
        { key: 'register', label: t.auth.register, onClick: () => {} },
      ]

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-label={t.auth.menuLabel}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className={`flex h-8 w-8 items-center justify-center overflow-hidden rounded-full border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
          open
            ? 'border-accent/60 bg-accent/15 text-text'
            : 'border-border bg-panel text-muted hover:border-accent/60 hover:text-text'
        }`}
      >
        {user ? (
          <span className="text-sm font-bold text-text">
            {(user.name ?? user.email ?? '?').charAt(0).toUpperCase()}
          </span>
        ) : (
          <UserIcon className="h-4 w-4" />
        )}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-2 w-44 overflow-hidden rounded-md border border-border bg-panel shadow-xl"
        >
          {user && (
            <div className="truncate border-b border-border px-3 py-2 text-xs text-muted">
              {user.email}
            </div>
          )}
          {items.map((it) => (
            <button
              key={it.key}
              type="button"
              role="menuitem"
              onClick={() => {
                it.onClick()
                setOpen(false)
              }}
              className={`block w-full px-3 py-2 text-left text-sm font-medium transition-colors hover:bg-accent/10 ${
                it.danger ? 'text-danger' : 'text-text'
              }`}
            >
              {it.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function Topbar({ page, onNavigate }) {
  const { lang, setLang, t } = useLang()
  const { muted, toggleMute, hasActiveAlarm } = useAppState()

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-bg/95 backdrop-blur">
      <div className="mx-auto max-w-[1600px] px-4 md:px-6">
        {/* Di lg+: grid 3 kolom → nav benar-benar di tengah layar */}
        <div className="flex h-14 items-center justify-between gap-3 md:h-16 lg:grid lg:grid-cols-[1fr_auto_1fr]">
          <div className="lg:justify-self-start">
            <Brand />
          </div>
          {/* Nav inline hanya di layar besar */}
          <div className="hidden lg:block lg:justify-self-center">
            <NavTabs page={page} onNavigate={onNavigate} />
          </div>
          <div className="flex items-center gap-2 md:gap-2.5 lg:justify-self-end">
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
              className={
                muted && hasActiveAlarm ? 'border-danger! text-danger!' : ''
              }
            >
              {muted ? (
                <VolumeMutedIcon className="h-4 w-4" />
              ) : (
                <VolumeIcon className="h-4 w-4" />
              )}
            </IconButton>
            <ProfileMenu />
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
