/**
 * Toggle switch generik (on/off).
 * Pakai: <Toggle checked={on} onChange={setOn} label="..." />
 */
export function Toggle({ checked, onChange, label, className = '' }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
        checked ? 'border-accent bg-accent' : 'border-border bg-panel'
      } ${className}`}
    >
      <span
        className={`inline-block h-3.5 w-3.5 transform rounded-full bg-text transition-transform ${
          checked ? 'translate-x-[18px]' : 'translate-x-[3px]'
        }`}
      />
    </button>
  )
}

/**
 * SegmentedToggle pilihan 2+ opsi (dipakai toggle bahasa ID/EN).
 * options: [{ value, label }], value aktif, onChange(value)
 */
export function SegmentedToggle({ options, value, onChange, label, className = '' }) {
  return (
    <div
      role="group"
      aria-label={label}
      className={`inline-flex overflow-hidden rounded-md border border-border ${className}`}
    >
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          aria-pressed={opt.value === value}
          onClick={() => onChange(opt.value)}
          className={`px-2.5 py-1 text-xs font-bold tracking-wide transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent ${
            opt.value === value
              ? 'bg-accent text-white'
              : 'bg-transparent text-muted hover:text-text'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
