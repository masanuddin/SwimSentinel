import { useLang } from '../i18n/LangContext'
import { Panel } from './ui/Panel'

/**
 * Placeholder halaman M0 — diganti konten asli di sprint M1–M4.
 * pageId: 'landing' | 'map' | 'simulation' | 'report'
 */
export function PagePlaceholder({ pageId }) {
  const { t } = useLang()
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold tracking-wide">{t.pageTitles[pageId]}</h1>
      <Panel>
        <div className="flex h-48 items-center justify-center">
          <p className="text-sm text-muted">{t.comingSoon}</p>
        </div>
      </Panel>
    </div>
  )
}
