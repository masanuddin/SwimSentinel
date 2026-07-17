import { useState } from 'react'
import { AppShell } from './components/layout/AppShell'
import { ToastHost } from './components/ToastHost'
import { AuthModal } from './components/AuthModal'
import { LandingPage } from './pages/LandingPage'
import { MapPage } from './pages/MapPage'
import { SimulationPage } from './pages/SimulationPage'
import { ReportPage } from './pages/ReportPage'

const PAGES = {
  landing: LandingPage,
  map: MapPage,
  simulation: SimulationPage,
  report: ReportPage,
}

export default function App() {
  const [page, setPage] = useState('landing')
  // null = tertutup, 'login' | 'register' = modal auth terbuka di mode itu
  const [authMode, setAuthMode] = useState(null)
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
          <Page onNavigate={setPage} />
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
