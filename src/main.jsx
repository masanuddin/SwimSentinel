import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { LangProvider } from './i18n/LangContext'
import { AppStateProvider } from './state/AppState'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <LangProvider>
      <AppStateProvider>
        <App />
      </AppStateProvider>
    </LangProvider>
  </StrictMode>,
)
