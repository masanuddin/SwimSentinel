# CLAUDE.md — Dashboard Monitoring Keselamatan Kolam

> Dokumen konteks untuk membangun dashboard di Claude Design (Fable 5), **per sprint**.
> Nama produk masih *placeholder*: **TirtaJaga** (silakan ganti). Bahasa build: Indonesia + toggle EN.

---

## 1. Konteks Proyek
- **Event:** Garuda Hacks 2026 — Track 2: Safety. Waktu ± 1 hari. Target: **Most Unique** (kekuatan = IoT di tengah mayoritas software).
- **Produk besar:** sistem IoT keselamatan kolam renang = **gelang gyro** (deteksi meronta di permukaan) + **kamera bawah air CV** (konfirmasi saat terendam) + **buzzer** (alarm keras) + **dashboard**.
- **Model gelang:** wajib dipinjamkan saat registrasi tamu, dipakai selama di kolam, dikembalikan saat keluar. Terbatas di area kolam.
- **Fokus artefak ini:** DASHBOARD MONITORING desktop (pos lifeguard). Demo dibuktikan lewat halaman Simulasi.

## 2. Masalah & Dampak (bahan halaman Landing)
- Tenggelam sering **senyap** (instinctive drowning response): korban tidak bisa teriak/melambai, diam vertikal 20–60 detik sebelum tenggelam — sering luput dari mata lifeguard.
- Banyak insiden terjadi **walau ada pengawas di dekatnya**.
- Sistem CV komersial mahal & butuh kamera terpasang; gelang lebih murah, ngasih lokasi presisi, dan nutup titik buta kamera (air keruh, kolam padat, silau).
- > ISI ANGKA INDONESIA di sini (statistik korban tenggelam / kolam). Belum diverifikasi — cari data resmi sebelum final.

## 3. Konsep Sistem — Sensor Fusion (ringkas, buat "Cara Kerja")
**Dua sensor, dua peran, saling nutup titik buta:**
1. **Fase meronta (di PERMUKAAN):** korban megap-megap 20–60 dtk sebelum terendam. Gelang masih di atas air → sinyal radio tembus → **gelang nembak "MERONTA!"** duluan. Cukup 1 paket kecil, gak perlu streaming.
2. **Fase terendam:** sinyal radio 2.4GHz (WiFi/BLE) **mati cepat di dalam air** (enclosure waterproof cuma lindungi elektronik, gak nolong rambatan sinyal). Saat gelang putus → **kamera bawah air ambil alih** buat konfirmasi tubuh diam terendam.
3. **Konfirmasi** via ambang durasi submersi → kurangi false alarm → **buzzer** bunyi + **dashboard** tampilkan lokasi + catat log.

**Kenapa gelang tetap andalan (jangan diturunkan jadi "cadangan kamera"):** gelang = pembeda & murah; nutup kondisi kamera buta (air keruh, kolam padat, silau, kolam tanpa kamera). Kamera nutup saat gelang terendam. Setara, bukan atasan-bawahan.

> **Jawaban juri (fisika sinyal di air):** "Sinyal radio memang lemah di dalam air — makanya gelang mendeteksi di fase meronta yang terjadi di permukaan, lalu kamera bawah air mengonfirmasi saat korban sudah terendam. Dua sensor saling menutup titik buta."

## 4. Arah Desain (WAJIB konsisten tiap sprint)
- **Vibe:** dark control-room / CCTV ops. Serius, tegas, fokus.
- **Warna (dark blue base):**
  - Background: `#0A1626` / panel `#122138` / border `#1E3350`
  - Aksen utama (biru): `#2D6CDF`
  - Status: aman `#22C55E` · waspada `#F5A623` · bahaya `#EF4444`
  - Teks: utama `#E6EDF5` · redup `#8CA0B8`
- **Tipografi:** sans modern (Inter/Geist). Angka data live pakai tabular/monospace.
- **Layout:** desktop-first (≥1280px), grid panel ala ops. Sidebar/topbar nav tetap.
- **Bilingual:** toggle **ID/EN** di header. Semua teks lewat satu kamus string (jangan hardcode kalimat).
- **Suara:** buzzer via Web Audio (bukan file eksternal). Ada tombol mute.

## 5. Peta Halaman
1. **Landing / Beranda** — hero (judul + 1 statistik nampar), blok masalah, "Cara Kerja" (gelang → buzzer → dashboard), CTA **"Buka Simulasi"**.
2. **Map** — kolam tampak atas, 4 zona. Status tiap zona live. Saat alarm: zona **merah berkedip** + pin + kartu korban (ID gelang, zona, timer submersi) + tombol **"Tanggapi"** + timer respons.
3. **Simulasi** — *bintang demo* (detail di §6).
4. **Report** — tabel alarm hari ini, grafik per bulan, statistik waktu respons, heatmap zona rawan, rekomendasi personil ("tambah 1 penjaga di Zona 3").

## 6. Halaman Simulasi (jantung demo — detail)
- **Kolam tampak ATAS**, dibagi **4 zona** (Zona 1–4) — konsisten dengan Map.
- Ada area **"deck"** di luar kolam.
- **Karakter kartun perenang.** 
  - **DRAG** = posisikan ke deck / zona. Posisi menentukan **zona yang muncul di Map**.
  - Di air (default) = state **"Berenang"** (hijau, animasi bob pelan) → ini "ngapung/aman".
  - **KLIK karakter** (atau tombol 🆘 kecil di karakter) = **picu urutan tenggelam**:
    1. **Meronta ~2 dtk** — karakter goyang, status **"Meronta"** (kuning). *(mirror: gyro variance tinggi)*
    2. **Diam & vertikal** — status **"Terdeteksi diam"** (oranye), **countdown submersi ~6 dtk** mulai. *(mirror: gyro flatline)*
    3. Countdown habis tanpa **"Tanggapi"** → **ALARM**: buzzer bunyi + notifikasi + zona di Map merah + tercatat di Report.
- Boleh taruh **beberapa** perenang di zona berbeda buat realisme; alarm nunjuk zona yang tepat.
- **Kenapa ada jeda deteksi:** nunjukin sistem **mengonfirmasi** dulu (bukan "di air = alarm"). Ini jawaban buat kekhawatiran juri soal false alarm.
- Catatan mekanik: **drag = lokasi, klik = pemicu.** Sengaja dipisah biar demo live antigagal (drag presisi rawan meleset).

## 7. Data Model (shared state, mock — dipakai lintas halaman)
```
swimmer  { id, name?, zoneId, status: 'idle'|'swimming'|'struggling'|'drowning'|'rescued', submersionSec, battery }
zone     { id: 1..4, label, riskCount }
alarm    { id, timestamp, zoneId, swimmerId, responseSec?, resolved: bool }
```
- **Satu sumber state** untuk seluruh app. Halaman **Simulasi menulis** event; **Map & Report membaca**.
- Tanpa backend. Semua in-memory (boleh seed beberapa alarm lama biar Report gak kosong).

## 8. Rencana Sprint (1 sprint = 1 prompt, jangan digabung)
- **M0 — Baseline:** design system + token warna/tipografi, app shell + navigasi 4 tab, toggle bahasa (kamus string ID/EN), shared state + tipe + mock data, routing antar halaman, halaman masih kosong (placeholder).
- **M1 — Landing:** hero, masalah, cara kerja, CTA.
- **M2 — Simulasi:** kolam 4 zona, perenang draggable, state Berenang, urutan Meronta→Diam→Countdown→Alarm, buzzer Web Audio, tulis event ke state.
- **M3 — Map:** kolam tampak atas 4 zona, status live, kartu korban + Tanggapi + timer, baca dari state.
- **M4 — Report:** tabel harian, grafik bulanan, statistik respons, heatmap zona, rekomendasi personil.
- **M5 — Polish (stretch):** toast notif, tombol mute, empty/edge states, animasi halus, kelengkapan 2 bahasa.

**Aturan tiap sprint:** patuhi design system §4, jaga konsistensi komponen, jangan bongkar hasil sprint sebelumnya.

## 9. Prinsip Menang (jangan lupa)
- Halaman **Simulasi harus JALAN live + buzzer bunyi** = momen wow.
- Konsisten **dark ops look** — jangan berubah tiap halaman.
- Semua **nyambung**: picu di Simulasi → muncul di Map + Report. Itu yang bikin sistemnya terasa nyata.
