import { useLang } from '../i18n/LangContext'
import { useAppState } from '../state/AppState'
import { Panel } from '../components/ui/Panel'
import { ShinyText } from '../components/ui/ShinyText'
import { ArrowRightIcon } from '../components/ui/Icons'

/**
 * M1 Landing: hero full-screen (video + shiny heading), blok masalah,
 * cara kerja (sensor fusion), CTA "Buka Simulasi".
 * Simulasi butuh login → CTA membuka modal login saat belum ada session;
 * setelah login, guard di App langsung mengarahkan ke area ber-login.
 * Video hero: public/hero.mp4 kalau file tidak ada, fallback ke
 * gradasi animasi (.hero-bg-anim), layout tetap aman.
 */

function CtaButton({ onClick, children, className = '' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group inline-flex items-center gap-2.5 rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-accent/85 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent md:px-8 md:py-4 md:text-base ${className}`}
    >
      {children}
      <ArrowRightIcon className="h-4 w-4 transition-transform group-hover:translate-x-1" />
    </button>
  )
}

function Hero({ L, onCta }) {
  return (
    <section className="relative flex h-[calc(100svh-6.5rem)] min-h-[540px] flex-col overflow-hidden lg:h-[calc(100vh-4rem)]">
      {/* Lapisan background: fallback animasi → video → overlay gelap */}
      <div className="hero-bg-anim absolute inset-0" />
      <video
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 h-full w-full object-cover"
      >
        <source src="/hero.mp4" type="video/mp4" />
      </video>
      <div className="absolute inset-0 bg-gradient-to-b from-bg/70 via-bg/40 to-bg" />

      <div className="relative z-10 mx-auto flex h-full w-full max-w-7xl flex-col px-4 py-6 md:px-6 md:py-8 lg:px-8">
        {/* Baris atas: lead kiri + statistik kanan */}
        <div className="grid gap-6 lg:grid-cols-2">
          <p className="max-w-xl text-sm text-text/80 md:text-base">
            {L.heroLead}
          </p>
          <div className="lg:text-right">
            <div className="num text-3xl font-bold text-text md:text-4xl">
              {L.heroStat}
            </div>
            <p className="mt-1 text-sm text-text/80 md:text-base">
              {L.heroStatCaption}
            </p>
          </div>
        </div>

        {/* Tengah: kicker + heading raksasa + CTA */}
        <div className="flex flex-1 flex-col items-center justify-center text-center">
          <p className="mb-4 text-xs uppercase tracking-tight text-text/80 md:text-sm">
            {L.kicker}
          </p>
          <h1 className="text-5xl font-medium leading-[0.85] tracking-tighter sm:text-6xl md:text-7xl lg:text-8xl xl:text-9xl">
            <span className="block text-white">{L.heroLine1}</span>
            <ShinyText className="block pb-2">{L.heroLine2}</ShinyText>
          </h1>
          <div className="mt-10">
            <CtaButton onClick={onCta}>{L.cta}</CtaButton>
          </div>
        </div>
      </div>
    </section>
  )
}

function SectionHeader({ kicker, heading }) {
  return (
    <div className="mb-8">
      <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-accent">
        {kicker}
      </p>
      <h2 className="text-2xl font-bold tracking-tight md:text-3xl">
        {heading}
      </h2>
    </div>
  )
}

function ProblemSection({ L }) {
  return (
    <section className="mx-auto w-full max-w-7xl px-4 py-12 md:px-6 md:py-16 lg:px-8">
      <SectionHeader kicker={L.problemKicker} heading={L.problemHeading} />
      <div className="grid gap-4 md:grid-cols-3">
        {L.problems.map((p) => (
          <Panel key={p.title}>
            <h3 className="mb-2 text-base font-semibold text-text">
              {p.title}
            </h3>
            <p className="text-sm leading-relaxed text-muted">{p.body}</p>
          </Panel>
        ))}
      </div>
    </section>
  )
}

function HowItWorksSection({ L }) {
  return (
    <section className="mx-auto w-full max-w-7xl px-4 py-12 md:px-6 md:py-16 lg:px-8">
      <SectionHeader kicker={L.howKicker} heading={L.howHeading} />
      <div className="grid gap-4 md:grid-cols-3">
        {L.steps.map((s, i) => (
          <Panel key={s.title}>
            <div className="num mb-3 inline-flex h-9 w-9 items-center justify-center rounded-md border border-accent/50 bg-accent/15 text-base font-bold text-accent">
              {i + 1}
            </div>
            <h3 className="mb-2 text-base font-semibold text-text">
              {s.title}
            </h3>
            <p className="text-sm leading-relaxed text-muted">{s.body}</p>
          </Panel>
        ))}
      </div>
      <blockquote className="mt-8 rounded-md border-l-2 border-accent bg-panel px-5 py-4 text-sm italic leading-relaxed text-muted md:text-base">
        {L.fusionNote}
      </blockquote>
    </section>
  )
}

function FinalCtaSection({ L, onCta }) {
  return (
    <section className="mx-auto w-full max-w-7xl px-4 pb-16 pt-4 md:px-6 md:pb-20 lg:px-8">
      <div className="rounded-md border border-border bg-panel px-6 py-12 text-center md:py-16">
        <h2 className="text-2xl font-bold tracking-tight md:text-3xl">
          {L.finalHeading}
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-sm text-muted md:text-base">
          {L.finalBody}
        </p>
        <div className="mt-8 flex justify-center">
          <CtaButton onClick={onCta}>{L.cta}</CtaButton>
        </div>
      </div>
    </section>
  )
}

export function LandingPage({ onNavigate, onOpenAuth }) {
  const { t } = useLang()
  const { user } = useAppState()
  const L = t.landing

  // Simulasi terproteksi: belum login → buka modal login dulu
  const handleCta = () =>
    user ? onNavigate('simulation') : onOpenAuth('login')

  return (
    <div>
      <Hero L={L} onCta={handleCta} />
      <ProblemSection L={L} />
      <HowItWorksSection L={L} />
      <FinalCtaSection L={L} onCta={handleCta} />
    </div>
  )
}
