import { useEffect, useState } from 'react'
import { useAppState } from './state/AppState'
import { AppShell } from './components/layout/AppShell'
import { ToastHost } from './components/ToastHost'
import { AuthModal } from './components/AuthModal'
import { LandingPage } from './pages/LandingPage'
import { MapPage } from './pages/MapPage'
import { SimulationPage } from './pages/SimulationPage'
import { ReportPage } from './pages/ReportPage'

const PAGES = {
  landing: LandingPage,
  dashboard: MapPage, // tab "Dashboard" = halaman peta pos lifeguard
  simulation: SimulationPage,
  report: ReportPage,
}

/** Halaman yang butuh login (guard di bawah). */
const PROTECTED_PAGES = ['dashboard', 'simulation', 'report']

export default function App() {
  const { user } = useAppState()
  const [page, setPage] = useState('landing')
  // null = tertutup, 'login' | 'register' = modal auth terbuka di mode itu
  const [authMode, setAuthMode] = useState(null)

  // Guard navigasi session Supabase (via `user` di AppState) sebagai
  // satu-satunya sumber kebenaran:
  // - belum login + halaman terproteksi → balik ke landing
  // - sudah login + di landing → redirect ke Dashboard (termasuk saat load
  //   dengan session tersimpan, selesai login, atau balik dari OAuth)
  useEffect(() => {
    if (!user && PROTECTED_PAGES.includes(page)) setPage('landing')
    else if (user && page === 'landing') setPage('dashboard')
  }, [user, page])

  // Login sukses dari mana pun → tutup modal auth kalau masih terbuka
  useEffect(() => {
    if (user) setAuthMode(null)
  }, [user])

  const Page = PAGES[page]

  return (
    <>
      <AppShell
        page={page}
        onNavigate={setPage}
        onOpenAuth={setAuthMode}
        fullBleed={page === 'landing'}
      >
        {/* key={page} → animasi fade halus tiap pindah halaman */}
        <div key={page} className="page-fade">
          <Page onNavigate={setPage} onOpenAuth={setAuthMode} />
        </div>
      </AppShell>
      <ToastHost onNavigate={setPage} />
      {authMode && (
        <AuthModal
          mode={authMode}
          onClose={() => setAuthMode(null)}
          onSwitchMode={setAuthMode}
        />
      )}
    </>
  )
}
