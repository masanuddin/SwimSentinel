/**
 * Panel/Card dasar ala ops dashboard: gelap, border tipis, sudut kecil.
 * `title` opsional → header dengan garis pemisah.
 */
export function Panel({ title, actions, className = '', children }) {
  return (
    <section
      className={`rounded-md border border-border bg-panel ${className}`}
    >
      {title != null && (
        <header className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted">
            {title}
          </h2>
          {actions}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  )
}
