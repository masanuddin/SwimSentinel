import { useEffect, useRef, useState } from 'react'
import { useLang } from '../../i18n/LangContext'
import { useAppState } from '../../state/AppState'
import { IconButton } from '../ui/Button'
import { SegmentedToggle } from '../ui/Toggle'
import { VolumeIcon, VolumeMutedIcon, UserIcon } from '../ui/Icons'

/**
 * Tab navigasi untuk user yang SUDAH login. Saat belum login, navbar
 * tidak menampilkan tab sama sekali (landing diakses via logo).
 * "Beranda" sengaja tidak ada — user login langsung diarahkan ke Map.
 */
const AUTH_NAV_IDS = ['dashboard', 'simulation', 'report']

function Brand({ onClick }) {
  const { t } = useLang()
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex cursor-pointer items-center gap-2.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:gap-3"
    >
      {/* /logo-nav.png = logo.png yang di-trim padding-nya (via ImageMagick) */}
      <img
        src="/logo-nav.png"
        alt=""
        className="h-9 w-9 select-none md:h-10 md:w-10"
        draggable="false"
      />
      <span className="text-sm font-bold tracking-wide md:text-base">
        {t.appName}
      </span>
    </button>
  )
}

function NavTabs({ page, onNavigate }) {
  const { t } = useLang()
  return (
    <nav
      className="flex items-center gap-1 whitespace-nowrap"
      aria-label={t.navLabel}
    >
      {AUTH_NAV_IDS.map((id) => {
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
function ProfileMenu({ onOpenAuth, onNavigate }) {
  const { t } = useLang()
  const { user, logout } = useAppState()
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

  // Belum login: ikon user = tombol Login langsung (tanpa dropdown).
  // Register tetap bisa diakses lewat tab di dalam modal.
  if (!user) {
    return (
      <button
        type="button"
        aria-label={t.auth.login}
        title={t.auth.login}
        onClick={() => onOpenAuth('login')}
        className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-panel text-muted transition-colors hover:border-accent/60 hover:text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        <UserIcon className="h-4 w-4" />
      </button>
    )
  }

  const items = [
    { key: 'dashboard', label: t.auth.dashboard, onClick: () => onNavigate('dashboard') },
    { key: 'logout', label: t.auth.logout, onClick: logout, danger: true },
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

function Topbar({ page, onNavigate, onOpenAuth }) {
  const { lang, setLang, t } = useLang()
  const { muted, toggleMute, hasActiveAlarm, user } = useAppState()

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-bg/95 backdrop-blur">
      <div className="mx-auto max-w-[1600px] px-4 md:px-6">
        {/* Di lg+: grid 3 kolom → nav benar-benar di tengah layar */}
        <div className="flex h-14 items-center justify-between gap-3 md:h-16 lg:grid lg:grid-cols-[1fr_auto_1fr]">
          <div className="lg:justify-self-start">
            {/* Logo: belum login → landing; sudah login → Dashboard (landing di-redirect) */}
            <Brand onClick={() => onNavigate(user ? 'dashboard' : 'landing')} />
          </div>
          {/* Nav inline hanya di layar besar & hanya saat sudah login */}
          <div className="hidden lg:block lg:justify-self-center">
            {user && <NavTabs page={page} onNavigate={onNavigate} />}
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
            <ProfileMenu onOpenAuth={onOpenAuth} onNavigate={onNavigate} />
          </div>
        </div>
        {/* Nav baris kedua di mobile/tablet (hanya saat sudah login) */}
        {user && (
          <div className="overflow-x-auto pb-2 lg:hidden">
            <NavTabs page={page} onNavigate={onNavigate} />
          </div>
        )}
      </div>
    </header>
  )
}

/**
 * AppShell: topbar (brand + nav 4 tab + kontrol) dan area konten.
 * Halaman aktif ditentukan `page` (view-switching, tanpa router).
 * fullBleed: halaman mengatur lebar/padding sendiri (dipakai Landing
 * untuk hero video selebar layar).
 * onOpenAuth('login'|'register'): buka modal auth (dipicu ProfileMenu).
 */
export function AppShell({ page, onNavigate, onOpenAuth, fullBleed = false, children }) {
  return (
    <div className="flex min-h-full flex-col bg-bg">
      <Topbar page={page} onNavigate={onNavigate} onOpenAuth={onOpenAuth} />
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
