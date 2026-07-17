import { useEffect, useState } from 'react'
import { useLang } from '../i18n/LangContext'
import { useAppState } from '../state/AppState'
import { Button } from './ui/Button'
import { Field } from './ui/Input'

/**
 * AuthModal — card Login/Register (desain dari wireframes/, diadaptasi ke
 * dark theme SwimSentinel). Tab di dalam card untuk pindah mode.
 *
 * CATATAN INTEGRASI: submit & tombol Google saat ini MOCK (langsung mengisi
 * `user` di AppState supaya UI logged-in bisa dites). Sesi berikutnya diganti
 * Supabase: signInWithPassword / signUp / signInWithOAuth('google').
 */

function GoogleIcon({ className = 'h-4 w-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.5 12.27c0-.85-.08-1.66-.22-2.45H12v4.64h6.45a5.52 5.52 0 0 1-2.4 3.62v3h3.87c2.27-2.09 3.58-5.17 3.58-8.81Z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.96-1.07 7.94-2.91l-3.87-3c-1.08.72-2.45 1.15-4.07 1.15-3.13 0-5.78-2.11-6.73-4.96H1.28v3.09A12 12 0 0 0 12 24Z"
      />
      <path
        fill="#FBBC05"
        d="M5.27 14.28a7.2 7.2 0 0 1 0-4.56V6.63H1.28a12 12 0 0 0 0 10.74l3.99-3.09Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.77c1.76 0 3.34.6 4.59 1.79l3.44-3.44A11.98 11.98 0 0 0 1.28 6.63l3.99 3.09C6.22 6.88 8.87 4.77 12 4.77Z"
      />
    </svg>
  )
}

function ModeTabs({ mode, onSwitchMode, A }) {
  return (
    <div className="grid grid-cols-2 gap-1 rounded-md border border-border bg-bg p-1">
      {['login', 'register'].map((m) => (
        <button
          key={m}
          type="button"
          aria-pressed={mode === m}
          onClick={() => onSwitchMode(m)}
          className={`rounded px-3 py-2 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent ${
            mode === m
              ? 'bg-accent text-white'
              : 'text-muted hover:text-text'
          }`}
        >
          {m === 'login' ? A.login : A.register}
        </button>
      ))}
    </div>
  )
}

export function AuthModal({ mode, onClose, onSwitchMode }) {
  const { t } = useLang()
  const A = t.auth
  const M = A.modal
  const { setUser } = useAppState()
  const [error, setError] = useState(null)

  const isLogin = mode === 'login'

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = ''
    }
  }, [onClose])

  const handleSwitch = (m) => {
    setError(null)
    onSwitchMode(m)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const email = fd.get('email')

    if (isLogin) {
      // TODO Supabase: supabase.auth.signInWithPassword({ email, password })
      setUser({ email })
    } else {
      if (fd.get('password') !== fd.get('passwordConfirm')) {
        setError(M.passwordMismatch)
        return
      }
      // TODO Supabase: supabase.auth.signUp({ email, password, options: { data } })
      setUser({ email, name: fd.get('fullName') })
    }
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={isLogin ? M.loginTitle : M.registerTitle}
        className="modal-in max-h-[90vh] w-full max-w-md overflow-y-auto rounded-md border border-border bg-panel p-6 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold tracking-tight">
              {isLogin ? M.loginTitle : M.registerTitle}
            </h2>
            <p className="mt-1 text-sm text-muted">
              {isLogin ? M.loginSubtitle : M.registerSubtitle}
            </p>
          </div>
          <button
            type="button"
            aria-label={M.close}
            onClick={onClose}
            className="shrink-0 text-muted transition-colors hover:text-text"
          >
            ✕
          </button>
        </div>

        <div className="mt-4">
          <ModeTabs mode={mode} onSwitchMode={handleSwitch} A={A} />
        </div>

        {/* key={mode} → field kereset saat pindah tab */}
        <form key={mode} onSubmit={handleSubmit} className="mt-4 space-y-3.5">
          {!isLogin && (
            <>
              <Field label={M.fullName} name="fullName" type="text" required />
              <Field label={M.phone} name="phone" type="tel" required />
            </>
          )}
          <Field label={M.email} name="email" type="email" required />
          <Field
            label={M.password}
            name="password"
            type="password"
            minLength={6}
            required
          />
          {!isLogin && (
            <Field
              label={M.passwordConfirm}
              name="passwordConfirm"
              type="password"
              error={Boolean(error)}
              required
            />
          )}

          {error && <p className="text-sm font-medium text-danger">{error}</p>}

          <Button type="submit" className="w-full justify-center py-2.5">
            {isLogin ? A.login : A.register}
          </Button>
        </form>

        <div className="my-4 flex items-center gap-3">
          <div className="h-px flex-1 bg-border" />
          <span className="text-[10px] font-semibold tracking-widest text-muted">
            {M.orContinueWith}
          </span>
          <div className="h-px flex-1 bg-border" />
        </div>

        {/* TODO Supabase: supabase.auth.signInWithOAuth({ provider: 'google' }) */}
        <Button variant="ghost" className="w-full justify-center py-2.5">
          <GoogleIcon />
          {M.google}
        </Button>

        <p className="mt-4 text-center text-xs text-muted">{M.terms}</p>
      </div>
    </div>
  )
}
