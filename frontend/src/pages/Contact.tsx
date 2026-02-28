import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles,
  Globe,
  Mail,
  MessageSquare,
  Send,
  Clock,
  CheckCircle2,
  ArrowLeft,
} from 'lucide-react'

const t = {
  en: {
    signIn: 'Sign in',
    getStarted: 'Get started',
    h1: 'Get in touch',
    subtitle: 'Have a question, feedback, or need help? We\'d love to hear from you.',
    name: 'Your name',
    email: 'Your email',
    subject: 'Subject',
    message: 'Your message',
    send: 'Send message',
    sending: 'Sending...',
    sent: 'Message sent! We\'ll get back to you within 24 hours.',
    responseTime: 'We typically respond within 24 hours',
    emailUs: 'Or email us directly',
    back: 'Back to home',
    footer: 'All rights reserved.',
    subjects: ['General question', 'Bug report', 'Feature request', 'Billing', 'Other'],
  },
  de: {
    signIn: 'Anmelden',
    getStarted: 'Jetzt starten',
    h1: 'Kontakt aufnehmen',
    subtitle: 'Hast du eine Frage, Feedback oder brauchst Hilfe? Wir freuen uns von dir zu hören.',
    name: 'Dein Name',
    email: 'Deine E-Mail',
    subject: 'Betreff',
    message: 'Deine Nachricht',
    send: 'Nachricht senden',
    sending: 'Wird gesendet...',
    sent: 'Nachricht gesendet! Wir melden uns innerhalb von 24 Stunden.',
    responseTime: 'Wir antworten in der Regel innerhalb von 24 Stunden',
    emailUs: 'Oder schreib uns direkt',
    back: 'Zurück zur Startseite',
    footer: 'Alle Rechte vorbehalten.',
    subjects: ['Allgemeine Frage', 'Fehlerbericht', 'Feature-Wunsch', 'Abrechnung', 'Sonstiges'],
  },
}

type Lang = keyof typeof t

export default function Contact() {
  const navigate = useNavigate()
  const [lang, setLang] = useState<Lang>(() => {
    const saved = localStorage.getItem('lang')
    if (saved === 'de' || saved === 'en') return saved
    return navigator.language.startsWith('de') ? 'de' : 'en'
  })
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' })
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

  const toggleLang = () => {
    const next = lang === 'en' ? 'de' : 'en'
    setLang(next)
    localStorage.setItem('lang', next)
  }

  const l = t[lang]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSending(true)
    try {
      await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      setSent(true)
      setForm({ name: '', email: '', subject: '', message: '' })
    } catch {
      // silently handle
    }
    setSending(false)
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white selection:bg-amber-500/30">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-amber-500/5 via-[#050505] to-[#050505]" />

      {/* Navbar */}
      <nav className="sticky top-0 z-50 border-b border-white/5 bg-[#050505]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div
            className="flex cursor-pointer items-center gap-3"
            onClick={() => navigate('/')}
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/20">
              <Sparkles className="h-4 w-4 text-amber-500" />
            </div>
            <span className="text-base font-bold tracking-tight">AutoApply</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleLang}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-2 text-[10px] font-black uppercase tracking-wider text-white/40 transition-colors hover:border-white/20 hover:text-white/70"
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
          </div>
        </div>
      </nav>

      {/* Content */}
      <section className="relative z-10 mx-auto max-w-2xl px-6 py-24">
        <button
          onClick={() => navigate('/')}
          className="mb-8 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-white/40 transition-colors hover:text-white/70"
        >
          <ArrowLeft className="h-4 w-4" />
          {l.back}
        </button>

        <div className="mb-4 flex items-center gap-3">
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
            <MessageSquare className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{l.h1}</h1>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
              {l.subtitle}
            </p>
          </div>
        </div>

        {sent ? (
          <div className="mt-12 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-8 text-center">
            <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-emerald-400" />
            <p className="text-lg font-bold text-emerald-400">{l.sent}</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 space-y-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <div className="space-y-2">
                <label className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
                  {l.name}
                </label>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full rounded-xl border border-white/10 bg-[#0A0A0A] px-4 py-3 text-sm text-white transition-colors placeholder:text-white/20 focus:border-amber-500/50 focus:outline-none"
                />
              </div>
              <div className="space-y-2">
                <label className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
                  {l.email}
                </label>
                <input
                  required
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full rounded-xl border border-white/10 bg-[#0A0A0A] px-4 py-3 text-sm text-white transition-colors placeholder:text-white/20 focus:border-amber-500/50 focus:outline-none"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
                {l.subject}
              </label>
              <select
                required
                value={form.subject}
                onChange={(e) => setForm({ ...form, subject: e.target.value })}
                className="w-full appearance-none rounded-xl border border-white/10 bg-[#0A0A0A] px-4 py-3 text-sm text-white transition-colors focus:border-amber-500/50 focus:outline-none"
              >
                <option value="">—</option>
                {l.subjects.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <label className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
                {l.message}
              </label>
              <textarea
                required
                rows={6}
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-[#0A0A0A] px-4 py-3 text-sm text-white transition-colors placeholder:text-white/20 focus:border-amber-500/50 focus:outline-none resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={sending}
              className="group flex w-full items-center justify-center gap-2 rounded-xl bg-amber-500 py-4 text-sm font-black uppercase tracking-wider text-black transition-all hover:bg-amber-400 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              {sending ? l.sending : l.send}
            </button>
          </form>
        )}

        <div className="mt-12 flex flex-col items-center gap-4 sm:flex-row sm:justify-between rounded-2xl border border-white/5 bg-[#0A0A0A] p-6">
          <div className="flex items-center gap-3">
            <Clock className="h-4 w-4 text-white/30" />
            <span className="text-xs text-white/40">{l.responseTime}</span>
          </div>
          <a
            href="mailto:2026@jobs-autoapply.com"
            className="flex items-center gap-2 text-xs font-bold text-amber-500 transition-colors hover:text-amber-400"
          >
            <Mail className="h-4 w-4" />
            2026@jobs-autoapply.com
          </a>
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
