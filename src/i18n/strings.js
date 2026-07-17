/**
 * Kamus string ID/EN. SEMUA teks UI lewat sini — jangan hardcode kalimat
 * di komponen. Tambah key baru di KEDUA bahasa sekaligus.
 */
export const strings = {
  id: {
    appName: 'TirtaJaga',
    appTagline: 'Pool Safety Monitoring',
    muteAlarm: 'Bisukan alarm',
    unmuteAlarm: 'Bunyikan alarm',
    comingSoon: 'Segera — sprint berikutnya',
    nav: {
      landing: 'Beranda',
      map: 'Map',
      simulation: 'Simulasi',
      report: 'Report',
    },
    pageTitles: {
      landing: 'Beranda',
      map: 'Peta Kolam',
      simulation: 'Simulasi',
      report: 'Laporan',
    },
    status: {
      safe: 'Aman',
      warn: 'Waspada',
      danger: 'Bahaya',
    },
    zone: 'Zona',
    landing: {
      kicker: 'Sistem Keselamatan Kolam Berbasis IoT',
      heroLine1: 'Deteksi Tenggelam.',
      heroLine2: 'Sebelum Terlambat.',
      heroLead:
        'TirtaJaga memadukan gelang sensor gyro dan kamera bawah air untuk menangkap tanda tenggelam yang senyap — lalu membunyikan alarm dan menunjukkan lokasi korban ke lifeguard dalam hitungan detik.',
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
    appName: 'TirtaJaga',
    appTagline: 'Pool Safety Monitoring',
    muteAlarm: 'Mute alarm',
    unmuteAlarm: 'Unmute alarm',
    comingSoon: 'Coming soon — next sprint',
    nav: {
      landing: 'Home',
      map: 'Map',
      simulation: 'Simulation',
      report: 'Report',
    },
    pageTitles: {
      landing: 'Home',
      map: 'Pool Map',
      simulation: 'Simulation',
      report: 'Report',
    },
    status: {
      safe: 'Safe',
      warn: 'Caution',
      danger: 'Danger',
    },
    zone: 'Zone',
    landing: {
      kicker: 'IoT-Powered Pool Safety System',
      heroLine1: 'Detect Drowning.',
      heroLine2: 'Before It’s Too Late.',
      heroLead:
        'TirtaJaga fuses a gyro-sensor wristband with an underwater camera to catch the silent signs of drowning — then sounds the alarm and pinpoints the victim for lifeguards within seconds.',
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
