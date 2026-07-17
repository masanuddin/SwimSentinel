import { createClient } from '@supabase/supabase-js'

/**
 * Client Supabase kredensial dari .env.local (prefix VITE_ wajib supaya
 * kebaca Vite). Kalau env belum diisi, `supabase` = null dan app jatuh ke
 * mode mock (login lokal tanpa backend) jadi teammate tanpa .env.local
 * tetap bisa jalanin demo.
 */
const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = url && anonKey ? createClient(url, anonKey) : null
