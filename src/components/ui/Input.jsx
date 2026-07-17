/**
 * Field — label + input teks gaya form gelap.
 * Pakai: <Field label="Email" name="email" type="email" required />
 * error: true → border merah (pesan error dirender terpisah oleh form).
 */
export function Field({ label, error = false, className = '', ...props }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-text">{label}</span>
      <input
        className={`w-full rounded-md border bg-bg px-3 py-2 text-sm text-text outline-none transition-colors placeholder:text-muted/60 ${
          error ? 'border-danger' : 'border-border focus:border-accent'
        } ${className}`}
        {...props}
      />
    </label>
  )
}
