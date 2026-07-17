const variants = {
  primary:
    'bg-accent text-white hover:bg-accent/85 border border-transparent',
  ghost:
    'bg-transparent text-muted border border-border hover:text-text hover:border-accent/60',
  danger:
    'bg-danger text-white hover:bg-danger/85 border border-transparent',
}

/**
 * Button dasar. variant: 'primary' | 'ghost' | 'danger'
 */
export function Button({ variant = 'primary', className = '', ...props }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center gap-2 rounded-md px-3.5 py-1.5 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`}
      {...props}
    />
  )
}

/**
 * IconButton: tombol kotak kecil untuk ikon (mis. mute). Wajib aria-label.
 */
export function IconButton({ label, active = false, className = '', children, ...props }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={`inline-flex h-8 w-8 items-center justify-center rounded-md border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
        active
          ? 'border-accent/60 bg-accent/15 text-text'
          : 'border-border bg-transparent text-muted hover:border-accent/60 hover:text-text'
      } ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
