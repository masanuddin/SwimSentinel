/**
 * Kamus string ID/EN. SEMUA teks UI lewat sini — jangan hardcode kalimat
 * di komponen. Tambah key baru di KEDUA bahasa sekaligus.
 */
export const strings = {
  id: {
    appName: 'SwimSentinel',
    muteAlarm: 'Bisukan alarm',
    unmuteAlarm: 'Bunyikan alarm',
    navLabel: 'Navigasi utama',
    auth: {
      menuLabel: 'Menu akun',
      login: 'Masuk',
      register: 'Daftar',
      dashboard: 'Dashboard',
      logout: 'Keluar',
      modal: {
        loginTitle: 'Masuk ke SwimSentinel',
        registerTitle: 'Daftar ke SwimSentinel',
        loginSubtitle:
          'Masuk untuk mengakses dashboard pemantauan keselamatan kolam.',
        registerSubtitle:
          'Buat akun untuk mulai memantau keselamatan kolam Anda.',
        fullName: 'Nama Lengkap',
        phone: 'Nomor Telepon',
        email: 'Email',
        password: 'Kata Sandi',
        passwordConfirm: 'Konfirmasi Kata Sandi',
        orContinueWith: 'ATAU LANJUT DENGAN',
        google: 'Lanjut dengan Google',
        terms: 'Dengan melanjutkan, Anda menyetujui Ketentuan Layanan kami.',
        passwordMismatch: 'Konfirmasi kata sandi tidak cocok.',
        close: 'Tutup',
        loading: 'Memproses…',
        checkEmail:
          'Pendaftaran berhasil — cek email Anda untuk konfirmasi, lalu login.',
        notConfigured:
          'Supabase belum dikonfigurasi — isi .env.local terlebih dahulu.',
      },
    },
    toast: {
      struggling: '{id} terdeteksi meronta — {zone}',
      alarm: 'ALARM — {zone} — {id}',
      resolved: '{id} diselamatkan — respons {sec} dtk',
      openDashboard: 'Lihat Dashboard',
    },
    nav: {
      landing: 'Beranda',
      dashboard: 'Dashboard',
      simulation: 'Simulasi',
      report: 'Report',
    },
    pageTitles: {
      landing: 'Beranda',
      dashboard: 'Peta Kolam',
      simulation: 'Simulasi',
      report: 'Laporan',
    },
    status: {
      safe: 'Aman',
      warn: 'Waspada',
      danger: 'Bahaya',
    },
    zone: 'Zona',
    report: {
      subtitle:
        'Rekap alarm, waktu respons, dan zona rawan — riwayat 6 bulan + kejadian live dari Simulasi.',
      tiles: {
        today: 'Alarm Hari Ini',
        total: 'Total Alarm (6 Bln)',
        avgResponse: 'Rata-rata Respons',
        fastest: 'Respons Tercepat',
      },
      monthlyPanel: 'Alarm per Bulan',
      heatmapPanel: 'Heatmap Zona Rawan',
      heatLow: 'Jarang',
      heatHigh: 'Sering',
      todayPanel: 'Alarm Hari Ini',
      todayEmpty: 'Belum ada alarm hari ini.',
      table: {
        time: 'Waktu',
        alarm: 'Alarm',
        band: 'Gelang',
        zone: 'Zona',
        response: 'Respons',
        status: 'Status',
      },
      statusDone: 'Selesai',
      statusActive: 'AKTIF',
      recPanel: 'Rekomendasi Personil',
      recStaff:
        'Tambah 1 penjaga di {zone} — {count} alarm ({pct}% dari total) dalam 6 bulan terakhir.',
      recResponseSlow:
        'Rata-rata waktu respons {avg} dtk — di atas target 15 dtk. Pertimbangkan pos jaga lebih dekat ke zona rawan.',
      recResponseGood:
        'Rata-rata waktu respons {avg} dtk — masih dalam target < 15 dtk. Pertahankan.',
      alarmsUnit: 'alarm',
    },
    map: {
      subtitle:
        'Pantauan langsung seluruh zona kolam — saat alarm, lokasi korban muncul di sini.',
      mapPanel: 'Peta Kolam — Live',
      zonesPanel: 'Status Zona',
      alarmsPanel: 'Alarm Aktif',
      respond: 'Tanggapi',
      responseTime: 'Respons',
      noAlarm: 'Tidak ada alarm aktif',
      allSafe: 'Semua zona terpantau aman.',
      swimmersShort: 'perenang',
      stats: {
        inWater: 'Di Air',
        onDeck: 'Di Deck',
        activeAlarms: 'Alarm Aktif',
      },
    },
    sim: {
      subtitle:
        'Drag karakter untuk memindahkan (deck ↔ kolam), klik karakter di air untuk memicu skenario tenggelam.',
      poolPanel: 'Kolam — Tampak Atas',
      deck: 'DECK',
      instructionsTitle: 'Cara Pakai',
      instructions: [
        'Drag karakter ke deck atau zona kolam — posisinya menentukan zona yang tampil di Map.',
        'Klik karakter yang sedang berenang untuk memicu skenario tenggelam.',
        'Sistem mengonfirmasi 6 detik sebelum alarm — tekan Selamatkan untuk membatalkan.',
      ],
      swimmersPanel: 'Perenang',
      addSwimmer: '+ Tambah',
      emptyPool: '💧 Drag perenang ke kolam untuk memulai',
      trigger: '🆘 Picu',
      rescue: 'Selamatkan',
      alarm: 'ALARM',
      submersion: 'Terendam',
      sec: ' dtk',
      battery: 'Baterai',
      swimmerStatus: {
        idle: 'Di Deck',
        swimming: 'Berenang',
        struggling: 'Meronta',
        drowning: 'Terdeteksi Diam',
        rescued: 'Diselamatkan',
      },
    },
    landing: {
      kicker: 'Sistem Keselamatan Kolam Berbasis IoT',
      heroLine1: 'Deteksi Tenggelam.',
      heroLine2: 'Sebelum Terlambat.',
      heroLead:
        'SwimSentinel memadukan gelang sensor gyro dan kamera bawah air untuk menangkap tanda tenggelam yang senyap — lalu membunyikan alarm dan menunjukkan lokasi korban ke lifeguard dalam hitungan detik.',
      heroStat: '±236.000',
      heroStatCaption: 'jiwa melayang akibat tenggelam setiap tahun di dunia — WHO',
      cta: 'Buka Simulasi',
      problemKicker: 'Masalahnya',
      problemHeading: 'Tenggelam tidak terlihat seperti di film',
      problems: [
        {
          title: 'Senyap, bukan teriak',
          body: 'Instinctive drowning response: korban tidak bisa berteriak atau melambai. Ia diam vertikal 20–60 detik sebelum terendam — mudah luput dari mata.',
        },
        {
          title: 'Terjadi di dekat pengawas',
          body: 'Banyak insiden terjadi walau lifeguard ada di lokasi. Di kolam yang ramai, "meronta" nyaris tak bisa dibedakan dari "bermain air".',
        },
        {
          title: 'Kamera saja tidak cukup',
          body: 'Sistem computer vision komersial mahal dan punya titik buta: air keruh, kolam padat, silau. Perlu sensor yang menempel di tubuh perenang itu sendiri.',
        },
      ],
      howKicker: 'Cara Kerja',
      howHeading: 'Dua sensor saling menutup titik buta',
      steps: [
        {
          title: 'Gelang mendeteksi meronta',
          body: 'Di permukaan, gyro pada gelang membaca gerakan meronta dan langsung mengirim sinyal darurat — sebelum korban terendam.',
        },
        {
          title: 'Kamera mengonfirmasi',
          body: 'Saat gelang terendam, sinyal radio padam di dalam air. Kamera bawah air mengambil alih dan memastikan tubuh diam melewati ambang durasi — bukan sekadar "di air = alarm".',
        },
        {
          title: 'Alarm + lokasi presisi',
          body: 'Buzzer berbunyi keras, dashboard menampilkan zona persis korban, dan insiden tercatat otomatis untuk laporan.',
        },
      ],
      fusionNote:
        '"Sinyal radio memang lemah di dalam air — karena itu gelang bekerja di fase meronta di permukaan, lalu kamera bawah air mengonfirmasi saat korban sudah terendam."',
      finalHeading: 'Lihat sistemnya bekerja',
      finalBody:
        'Picu skenario tenggelam di halaman Simulasi: alarm berbunyi, zona menyala merah di Map, dan insiden tercatat di Report — semuanya live.',
    },
  },
  en: {
    appName: 'SwimSentinel',
    muteAlarm: 'Mute alarm',
    unmuteAlarm: 'Unmute alarm',
    navLabel: 'Main navigation',
    auth: {
      menuLabel: 'Account menu',
      login: 'Login',
      register: 'Register',
      dashboard: 'Dashboard',
      logout: 'Log Out',
      modal: {
        loginTitle: 'Log into SwimSentinel',
        registerTitle: 'Register to SwimSentinel',
        loginSubtitle: 'Log in to access the pool safety monitoring dashboard.',
        registerSubtitle: 'Create an account to start monitoring your pool’s safety.',
        fullName: 'Full Name',
        phone: 'Phone Number',
        email: 'Email',
        password: 'Password',
        passwordConfirm: 'Password Confirmation',
        orContinueWith: 'OR CONTINUE WITH',
        google: 'Continue with Google',
        terms: 'By clicking continue, you are agreeing to our Terms of Service.',
        passwordMismatch: 'Password confirmation does not match.',
        close: 'Close',
        loading: 'Processing…',
        checkEmail:
          'Registration successful — check your email to confirm, then log in.',
        notConfigured:
          'Supabase is not configured — fill in .env.local first.',
      },
    },
    toast: {
      struggling: '{id} struggling detected — {zone}',
      alarm: 'ALARM — {zone} — {id}',
      resolved: '{id} rescued — {sec}s response',
      openDashboard: 'View Dashboard',
    },
    nav: {
      landing: 'Home',
      dashboard: 'Dashboard',
      simulation: 'Simulation',
      report: 'Report',
    },
    pageTitles: {
      landing: 'Home',
      dashboard: 'Pool Map',
      simulation: 'Simulation',
      report: 'Report',
    },
    status: {
      safe: 'Safe',
      warn: 'Caution',
      danger: 'Danger',
    },
    zone: 'Zone',
    report: {
      subtitle:
        'Alarm recap, response times, and risk zones — 6 months of history plus live events from the Simulation.',
      tiles: {
        today: 'Alarms Today',
        total: 'Total Alarms (6 Mo)',
        avgResponse: 'Avg Response',
        fastest: 'Fastest Response',
      },
      monthlyPanel: 'Alarms per Month',
      heatmapPanel: 'Zone Risk Heatmap',
      heatLow: 'Rare',
      heatHigh: 'Frequent',
      todayPanel: 'Alarms Today',
      todayEmpty: 'No alarms today.',
      table: {
        time: 'Time',
        alarm: 'Alarm',
        band: 'Wristband',
        zone: 'Zone',
        response: 'Response',
        status: 'Status',
      },
      statusDone: 'Resolved',
      statusActive: 'ACTIVE',
      recPanel: 'Staffing Recommendation',
      recStaff:
        'Add 1 lifeguard to {zone} — {count} alarms ({pct}% of total) in the last 6 months.',
      recResponseSlow:
        'Average response time is {avg}s — above the 15s target. Consider a guard post closer to the risk zone.',
      recResponseGood:
        'Average response time is {avg}s — within the < 15s target. Keep it up.',
      alarmsUnit: 'alarms',
    },
    map: {
      subtitle:
        'Live view of every pool zone — when an alarm fires, the victim’s location appears here.',
      mapPanel: 'Pool Map — Live',
      zonesPanel: 'Zone Status',
      alarmsPanel: 'Active Alarms',
      respond: 'Respond',
      responseTime: 'Response',
      noAlarm: 'No active alarms',
      allSafe: 'All zones monitored and safe.',
      swimmersShort: 'swimmers',
      stats: {
        inWater: 'In Water',
        onDeck: 'On Deck',
        activeAlarms: 'Active Alarms',
      },
    },
    sim: {
      subtitle:
        'Drag a character to move them (deck ↔ pool), click a character in the water to trigger a drowning scenario.',
      poolPanel: 'Pool — Top View',
      deck: 'DECK',
      instructionsTitle: 'How to Use',
      instructions: [
        'Drag a character onto the deck or a pool zone — their position sets the zone shown on the Map.',
        'Click a swimming character to trigger a drowning scenario.',
        'The system confirms for 6 seconds before alarming — press Rescue to cancel.',
      ],
      swimmersPanel: 'Swimmers',
      addSwimmer: '+ Add',
      emptyPool: '💧 Drag a swimmer into the pool to start',
      trigger: '🆘 Trigger',
      rescue: 'Rescue',
      alarm: 'ALARM',
      submersion: 'Submerged',
      sec: 's',
      battery: 'Battery',
      swimmerStatus: {
        idle: 'On Deck',
        swimming: 'Swimming',
        struggling: 'Struggling',
        drowning: 'Motionless Detected',
        rescued: 'Rescued',
      },
    },
    landing: {
      kicker: 'IoT-Powered Pool Safety System',
      heroLine1: 'Detect Drowning.',
      heroLine2: 'Before It’s Too Late.',
      heroLead:
        'SwimSentinel fuses a gyro-sensor wristband with an underwater camera to catch the silent signs of drowning — then sounds the alarm and pinpoints the victim for lifeguards within seconds.',
      heroStat: '±236,000',
      heroStatCaption: 'lives lost to drowning every year worldwide — WHO',
      cta: 'Open Simulation',
      problemKicker: 'The Problem',
      problemHeading: 'Drowning doesn’t look like it does in movies',
      problems: [
        {
          title: 'Silent, not screaming',
          body: 'The instinctive drowning response: victims can’t shout or wave. They stay silently vertical for 20–60 seconds before submerging — easy to miss.',
        },
        {
          title: 'It happens near lifeguards',
          body: 'Many incidents occur even with lifeguards on duty. In a crowded pool, "struggling" is nearly indistinguishable from "playing".',
        },
        {
          title: 'Cameras alone aren’t enough',
          body: 'Commercial computer-vision systems are expensive and have blind spots: murky water, crowded pools, glare. You need a sensor on the swimmer’s own body.',
        },
      ],
      howKicker: 'How It Works',
      howHeading: 'Two sensors covering each other’s blind spots',
      steps: [
        {
          title: 'Wristband detects struggling',
          body: 'At the surface, the wristband’s gyro reads struggling motion and fires an emergency signal — before the victim goes under.',
        },
        {
          title: 'Camera confirms',
          body: 'Once the wristband submerges, radio signals die underwater. The underwater camera takes over, confirming a motionless body past a duration threshold — not just "in water = alarm".',
        },
        {
          title: 'Alarm + precise location',
          body: 'The buzzer sounds, the dashboard shows the victim’s exact zone, and the incident is logged automatically for reports.',
        },
      ],
      fusionNote:
        '"Radio signals are indeed weak underwater — that’s why the wristband works during the surface struggling phase, and the underwater camera confirms once the victim submerges."',
      finalHeading: 'See the system in action',
      finalBody:
        'Trigger a drowning scenario on the Simulation page: the alarm sounds, the zone turns red on the Map, and the incident is logged in Reports — all live.',
    },
  },
}
