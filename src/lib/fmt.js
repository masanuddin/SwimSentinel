/** Interpolasi template kamus: fmt('{zone} rawan', { zone: 'Zona 3' }) */
export const fmt = (s, vars) => s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k]))
