import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles,
  ArrowRight,
  Upload,
  Target,
  Bot,
  LogIn,
  UserCircle,
  MailCheck,
  ExternalLink,
  Shield,
  Monitor,
  BriefcaseBusiness,
  FileText,
  Ban,
  Check,
  Zap,
  Globe,
  Star,
  Mail,
  MessageSquare,
} from 'lucide-react'

const t = {
  en: {
    signIn: 'Sign in',
    getStarted: 'Get started',
    heroBadge: 'AI-powered job applications',
    heroH1: 'Apply to hundreds of jobs ',
    heroH1Span: 'while you sleep.',
    heroP:
      'AutoApply scans StepStone and LinkedIn for your target roles and submits applications automatically — CV, cover letter, and all form fields handled.',
    ctaMain: 'Start applying — €8/mo',
    ctaSecondary: 'See how it works',
    trusted: 'Trusted by job seekers across Germany',
    howLabel: 'How it works',
    howH2: 'Six steps. Zero effort.',
    steps: [
      {
        title: 'Log in',
        desc: 'Create your account and sign in to access the AutoApply dashboard.',
      },
      {
        title: 'Fill your profile',
        desc: 'Add your personal info, work experience, and answer common application questions.',
      },
      {
        title: 'Upload your CV',
        desc: 'Upload one or multiple CVs. AutoApply picks the best match for each role.',
      },
      {
        title: 'Start the bot',
        desc: 'The bot scans platforms, finds matching jobs, and submits applications automatically.',
      },
      {
        title: 'Check your inbox',
        desc: 'Sit back and wait for interview invitations to land in your email.',
      },
      {
        title: 'Apply externally',
        desc: 'Found a job yourself? Add it to your list and let the bot apply for you.',
      },
    ],
    featLabel: 'Features',
    featH2: 'Everything you need to land your next job.',
    features: [
      {
        title: 'Multi-platform',
        desc: 'StepStone, Xing, and LinkedIn — apply across all major German job boards.',
      },
      {
        title: 'Smart form filling',
        desc: 'AI matches your profile to application forms. Cover letters, salary, availability — all handled.',
      },
      {
        title: 'CV management',
        desc: 'Upload multiple CVs for different roles. The bot picks the best one per application.',
      },
      {
        title: 'Live monitoring',
        desc: 'Watch the bot work in real-time. See every field filled, every application submitted.',
      },
      {
        title: 'Blacklists',
        desc: 'Skip companies, keywords, or job types you want to avoid. Full control over where you apply.',
      },
      {
        title: 'Anti-detection',
        desc: 'Human-like timing and behavior patterns. Your applications look natural.',
      },
    ],
    priceLabel: 'Pricing',
    priceH2: 'Simple pricing. Cancel anytime.',
    priceItems: [
      'All platforms included',
      'Unlimited applications',
      'Real-time bot monitoring',
      'Multiple CV management',
      'Smart AI form filling',
      'Cancel anytime',
    ],
    reviewsLabel: 'Reviews',
    reviewsH2: 'What our users say.',
    reviews: [
      {
        name: 'Markus W.',
        role: 'Software Engineer, Berlin',
        quote: 'I got 12 interview invitations in my first week. AutoApply saved me dozens of hours of manual applications.',
      },
      {
        name: 'Sarah K.',
        role: 'Marketing Manager, Munich',
        quote: 'The bot filled out every form perfectly — even tricky questions about salary expectations and availability.',
      },
      {
        name: 'Thomas L.',
        role: 'Data Analyst, Hamburg',
        quote: 'I was skeptical at first, but the live monitoring convinced me. You can see exactly what the bot does in real-time.',
      },
    ],
    contactLabel: 'Contact',
    contactH2: 'Have questions?',
    contactP: 'We usually respond within 24 hours.',
    contactCta: 'Send us a message',
    contactEmail: '2026@jobs-autoapply.com',
    footer: 'All rights reserved.',
  },
  de: {
    signIn: 'Anmelden',
    getStarted: 'Jetzt starten',
    heroBadge: 'KI-gestützte Bewerbungen',
    heroH1: 'Bewirb dich auf hunderte Jobs ',
    heroH1Span: 'während du schläfst.',
    heroP:
      'AutoApply durchsucht StepStone und LinkedIn nach passenden Stellen und verschickt Bewerbungen automatisch — Lebenslauf, Anschreiben und alle Formularfelder inklusive.',
    ctaMain: 'Jetzt bewerben — 8 €/Monat',
    ctaSecondary: 'So funktioniert es',
    trusted: 'Vertraut von Jobsuchenden in ganz Deutschland',
    howLabel: 'So funktioniert es',
    howH2: 'Sechs Schritte. Null Aufwand.',
    steps: [
      {
        title: 'Einloggen',
        desc: 'Erstelle dein Konto und melde dich an, um auf das AutoApply-Dashboard zuzugreifen.',
      },
      {
        title: 'Profil ausfüllen',
        desc: 'Füge persönliche Daten, Berufserfahrung und Antworten auf häufige Bewerbungsfragen hinzu.',
      },
      {
        title: 'Lebenslauf hochladen',
        desc: 'Lade einen oder mehrere Lebensläufe hoch. AutoApply wählt den besten für jede Stelle.',
      },
      {
        title: 'Bot starten',
        desc: 'Der Bot durchsucht Plattformen, findet passende Jobs und bewirbt sich automatisch.',
      },
      {
        title: 'Posteingang prüfen',
        desc: 'Lehne dich zurück und warte auf Einladungen zu Vorstellungsgesprächen in deinem Postfach.',
      },
      {
        title: 'Extern bewerben',
        desc: 'Einen Job selbst gefunden? Füge ihn zur Liste hinzu und lass den Bot sich für dich bewerben.',
      },
    ],
    featLabel: 'Funktionen',
    featH2: 'Alles, was du brauchst, um deinen nächsten Job zu finden.',
    features: [
      {
        title: 'Multi-Plattform',
        desc: 'StepStone, Xing und LinkedIn — bewirb dich auf allen großen deutschen Jobbörsen.',
      },
      {
        title: 'Intelligente Formularfelder',
        desc: 'KI gleicht dein Profil mit den Bewerbungsformularen ab. Anschreiben, Gehalt, Verfügbarkeit — alles erledigt.',
      },
      {
        title: 'Lebenslauf-Verwaltung',
        desc: 'Lade mehrere Lebensläufe für verschiedene Rollen hoch. Der Bot wählt den passendsten.',
      },
      {
        title: 'Live-Überwachung',
        desc: 'Beobachte den Bot in Echtzeit. Sieh jedes ausgefüllte Feld, jede gesendete Bewerbung.',
      },
      {
        title: 'Blacklists',
        desc: 'Überspringe Unternehmen, Keywords oder Jobtypen. Volle Kontrolle, wo du dich bewirbst.',
      },
      {
        title: 'Anti-Erkennung',
        desc: 'Menschliches Timing und Verhaltensmuster. Deine Bewerbungen wirken natürlich.',
      },
    ],
    priceLabel: 'Preise',
    priceH2: 'Einfache Preise. Jederzeit kündbar.',
    priceItems: [
      'Alle Plattformen inklusive',
      'Unbegrenzte Bewerbungen',
      'Echtzeit-Bot-Überwachung',
      'Mehrere Lebensläufe verwalten',
      'KI-gestützte Formularfelder',
      'Jederzeit kündbar',
    ],
    reviewsLabel: 'Bewertungen',
    reviewsH2: 'Was unsere Nutzer sagen.',
    reviews: [
      {
        name: 'Markus W.',
        role: 'Software-Entwickler, Berlin',
        quote: 'Ich habe in meiner ersten Woche 12 Einladungen zu Vorstellungsgesprächen bekommen. AutoApply hat mir dutzende Stunden erspart.',
      },
      {
        name: 'Sarah K.',
        role: 'Marketing-Managerin, München',
        quote: 'Der Bot hat jedes Formular perfekt ausgefüllt — sogar knifflige Fragen zu Gehaltsvorstellungen und Verfügbarkeit.',
      },
      {
        name: 'Thomas L.',
        role: 'Datenanalyst, Hamburg',
        quote: 'Ich war anfangs skeptisch, aber die Live-Überwachung hat mich überzeugt. Man sieht genau, was der Bot in Echtzeit macht.',
      },
    ],
    contactLabel: 'Kontakt',
    contactH2: 'Noch Fragen?',
    contactP: 'Wir antworten in der Regel innerhalb von 24 Stunden.',
    contactCta: 'Nachricht senden',
    contactEmail: '2026@jobs-autoapply.com',
    footer: 'Alle Rechte vorbehalten.',
  },
}

type Lang = keyof typeof t

export default function LandingPage() {
  const navigate = useNavigate()
  const [lang, setLang] = useState<Lang>(() => {
    const saved = localStorage.getItem('lang')
    if (saved === 'de' || saved === 'en') return saved
    return navigator.language.startsWith('de') ? 'de' : 'en'
  })

  const toggleLang = () => {
    const next = lang === 'en' ? 'de' : 'en'
    setLang(next)
    localStorage.setItem('lang', next)
  }

  const l = t[lang]
  const stepIcons = [LogIn, UserCircle, Upload, Bot, MailCheck, ExternalLink]
  const featIcons = [BriefcaseBusiness, Sparkles, FileText, Monitor, Ban, Shield]

  return (
    <div className="min-h-screen bg-[#050505] text-white selection:bg-amber-500/30">
      {/* Background */}
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-amber-500/5 via-[#050505] to-[#050505]" />

      {/* Navbar */}
      <nav className="sticky top-0 z-50 border-b border-white/5 bg-[#050505]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/20">
              <Sparkles className="h-4 w-4 text-amber-500" />
            </div>
            <span className="text-base font-bold tracking-tight">AutoApply</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleLang}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-2 text-[10px] font-black uppercase tracking-wider text-white/40 transition-colors hover:border-white/20 hover:text-white/70"
              title={lang === 'en' ? 'Auf Deutsch wechseln' : 'Switch to English'}
            >
              <Globe className="h-3.5 w-3.5" />
              {lang === 'en' ? 'DE' : 'EN'}
            </button>
            <button
              onClick={() => navigate('/login')}
              className="rounded-lg border border-white/10 px-4 py-2 text-xs font-bold uppercase tracking-wider text-white/60 transition-colors hover:border-white/20 hover:text-white"
            >
              {l.signIn}
            </button>
            <button
              onClick={() => navigate('/login?register=1')}
              className="rounded-lg bg-amber-500 px-4 py-2 text-xs font-bold uppercase tracking-wider text-black transition-colors hover:bg-amber-400"
            >
              {l.getStarted}
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-4xl px-6 pb-24 pt-24 text-center md:pt-32">
        <div className="mx-auto mb-8 inline-flex items-center gap-2 rounded-full border border-amber-500/20 bg-amber-500/5 px-4 py-1.5">
          <Zap className="h-3 w-3 text-amber-500" />
          <span className="text-[11px] font-bold uppercase tracking-wider text-amber-500">
            {l.heroBadge}
          </span>
        </div>

        <h1 className="mb-6 text-5xl font-black leading-tight tracking-tight md:text-7xl">
          {l.heroH1}
          <span className="bg-gradient-to-r from-amber-400 to-amber-600 bg-clip-text text-transparent">
            {l.heroH1Span}
          </span>
        </h1>

        <p className="mx-auto mb-10 max-w-2xl text-lg text-white/50 leading-relaxed">{l.heroP}</p>

        <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <button
            onClick={() => navigate('/login?register=1')}
            className="group relative flex items-center gap-2 overflow-hidden rounded-xl bg-amber-500 px-8 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_30px_rgba(245,158,11,0.3)] transition-all hover:bg-amber-400 hover:shadow-[0_0_40px_rgba(245,158,11,0.4)]"
          >
            <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
            <span className="relative">{l.ctaMain}</span>
            <ArrowRight className="relative h-4 w-4 transition-transform group-hover:translate-x-1" />
          </button>
          <a
            href="#how-it-works"
            className="flex items-center gap-2 rounded-xl border border-white/10 px-8 py-4 text-sm font-bold uppercase tracking-wider text-white/60 transition-colors hover:border-white/20 hover:text-white"
          >
            {l.ctaSecondary}
          </a>
        </div>

        <p className="mt-12 text-xs font-medium uppercase tracking-widest text-white/20">
          {l.trusted}
        </p>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="relative z-10 border-t border-white/5 py-24">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-16 text-center">
            <span className="text-[9px] font-black uppercase tracking-[0.2em] text-amber-500">
              {l.howLabel}
            </span>
            <h2 className="mt-4 text-3xl font-black tracking-tight md:text-4xl">{l.howH2}</h2>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {l.steps.map(({ title, desc }, i) => {
              const Icon = stepIcons[i]
              const step = String(i + 1).padStart(2, '0')
              return (
                <div
                  key={step}
                  className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-8 transition-colors hover:border-white/10"
                >
                  <span className="text-[10px] font-black tracking-widest text-amber-500/50">
                    STEP {step}
                  </span>
                  <div className="mt-4 mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/20">
                    <Icon className="h-6 w-6 text-amber-500" />
                  </div>
                  <h3 className="mb-2 text-lg font-bold">{title}</h3>
                  <p className="text-sm leading-relaxed text-white/40">{desc}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="relative z-10 border-t border-white/5 py-24">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-16 text-center">
            <span className="text-[9px] font-black uppercase tracking-[0.2em] text-amber-500">
              {l.featLabel}
            </span>
            <h2 className="mt-4 text-3xl font-black tracking-tight md:text-4xl">{l.featH2}</h2>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {l.features.map(({ title, desc }, i) => {
              const Icon = featIcons[i]
              return (
                <div
                  key={title}
                  className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 transition-colors hover:border-white/10"
                >
                  <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-white/5">
                    <Icon className="h-5 w-5 text-amber-500" />
                  </div>
                  <h3 className="mb-1 text-sm font-bold">{title}</h3>
                  <p className="text-xs leading-relaxed text-white/40">{desc}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Reviews */}
      <section className="relative z-10 border-t border-white/5 py-24">
        <div className="mx-auto max-w-6xl px-6">
          <div className="mb-16 text-center">
            <span className="text-[9px] font-black uppercase tracking-[0.2em] text-amber-500">
              {l.reviewsLabel}
            </span>
            <h2 className="mt-4 text-3xl font-black tracking-tight md:text-4xl">
              {l.reviewsH2}
            </h2>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {l.reviews.map(({ name, role, quote }) => (
              <div
                key={name}
                className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-8 transition-colors hover:border-white/10"
              >
                <div className="mb-4 flex gap-1">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star
                      key={i}
                      className="h-4 w-4 fill-amber-500 text-amber-500"
                    />
                  ))}
                </div>
                <p className="mb-6 text-sm leading-relaxed text-white/60">"{quote}"</p>
                <div className="flex items-center gap-3 border-t border-white/5 pt-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-500/10 text-xs font-black text-amber-500">
                    {name.split(' ').map((n) => n[0]).join('')}
                  </div>
                  <div>
                    <p className="text-sm font-bold">{name}</p>
                    <p className="text-[10px] text-white/40">{role}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="relative z-10 border-t border-white/5 py-24">
        <div className="mx-auto max-w-md px-6 text-center">
          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-amber-500">
            {l.priceLabel}
          </span>
          <h2 className="mt-4 mb-10 text-3xl font-black tracking-tight md:text-4xl">
            {l.priceH2}
          </h2>

          <div className="rounded-2xl border border-amber-500/20 bg-[#0A0A0A] p-8 shadow-[0_0_40px_rgba(245,158,11,0.05)]">
            <div className="mb-6">
              <span className="text-5xl font-black">€8</span>
              <span className="text-lg text-white/40">
                {' '}
                / {lang === 'de' ? 'Monat' : 'month'}
              </span>
            </div>

            <ul className="mb-8 space-y-3 text-left">
              {l.priceItems.map((item) => (
                <li key={item} className="flex items-center gap-3 text-sm text-white/60">
                  <Check className="h-4 w-4 shrink-0 text-amber-500" />
                  {item}
                </li>
              ))}
            </ul>

            <button
              onClick={() => navigate('/login?register=1')}
              className="group relative w-full overflow-hidden rounded-xl bg-amber-500 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_20px_rgba(245,158,11,0.2)] transition-all hover:bg-amber-400"
            >
              <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
              <span className="relative">{l.getStarted}</span>
            </button>
          </div>
        </div>
      </section>

      {/* Contact */}
      <section className="relative z-10 border-t border-white/5 py-24">
        <div className="mx-auto max-w-2xl px-6 text-center">
          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-amber-500">
            {l.contactLabel}
          </span>
          <h2 className="mt-4 mb-4 text-3xl font-black tracking-tight md:text-4xl">
            {l.contactH2}
          </h2>
          <p className="mb-8 text-sm text-white/40">{l.contactP}</p>

          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <button
              onClick={() => navigate('/contact')}
              className="group flex items-center gap-2 rounded-xl bg-amber-500 px-8 py-4 text-sm font-black uppercase tracking-wider text-black transition-all hover:bg-amber-400"
            >
              <MessageSquare className="h-4 w-4" />
              {l.contactCta}
            </button>
            <a
              href={`mailto:${l.contactEmail}`}
              className="flex items-center gap-2 rounded-xl border border-white/10 px-8 py-4 text-sm font-bold text-white/60 transition-colors hover:border-white/20 hover:text-white"
            >
              <Mail className="h-4 w-4" />
              {l.contactEmail}
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/5 py-12">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <div className="flex items-center gap-3">
              <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-amber-500/10 border border-amber-500/20">
                <Sparkles className="h-3 w-3 text-amber-500" />
              </div>
              <span className="text-sm font-bold">AutoApply</span>
            </div>
            <p className="text-xs text-white/20">
              &copy; {new Date().getFullYear()} AutoApply. {l.footer}
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
