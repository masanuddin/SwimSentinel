import { createContext, useContext, useMemo, useState } from 'react'
import { strings } from './strings'

const LangContext = createContext(null)

export function LangProvider({ children }) {
  const [lang, setLang] = useState('id')

  const value = useMemo(
    () => ({ lang, setLang, t: strings[lang] }),
    [lang],
  )

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>
}

/**
 * useLang() → { lang: 'id'|'en', setLang, t }
 * `t` = kamus bahasa aktif, contoh: t.nav.map, t.status.safe
 */
export function useLang() {
  const ctx = useContext(LangContext)
  if (!ctx) throw new Error('useLang harus dipakai di dalam <LangProvider>')
  return ctx
}
