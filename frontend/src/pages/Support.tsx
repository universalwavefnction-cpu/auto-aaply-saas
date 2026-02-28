import { useState } from 'react'
import {
  MessageSquare,
  Send,
  Clock,
  Mail,
  CheckCircle2,
} from 'lucide-react'

const SUBJECTS = ['General question', 'Bug report', 'Feature request', 'Billing', 'Other']

export default function Support() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' })
  const [sending, setSending] = useState(false)
  const [sent, setSent] = useState(false)

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
    } catch {}
    setSending(false)
  }

  return (
    <div className="space-y-8 p-8 max-w-2xl mx-auto">
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
          <MessageSquare className="h-5 w-5 text-amber-500" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Support</h1>
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
            Get help or send feedback
          </p>
        </div>
      </div>

      {sent ? (
        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-8 text-center">
          <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-emerald-400" />
          <p className="text-lg font-bold text-emerald-400">Message sent!</p>
          <p className="mt-2 text-sm text-white/40">We'll get back to you within 24 hours.</p>
          <button
            onClick={() => setSent(false)}
            className="mt-6 rounded-xl border border-white/10 px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-white/60 transition-colors hover:bg-white/5"
          >
            Send another message
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6 rounded-2xl border border-white/10 bg-[#0A0A0A] p-8 shadow-2xl">
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
                Your name
              </label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white transition-colors placeholder:text-white/20 focus:border-amber-500/50 focus:outline-none"
              />
            </div>
            <div className="space-y-2">
              <label className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
                Your email
              </label>
              <input
                required
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white transition-colors placeholder:text-white/20 focus:border-amber-500/50 focus:outline-none"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
              Subject
            </label>
            <select
              required
              value={form.subject}
              onChange={(e) => setForm({ ...form, subject: e.target.value })}
              className="w-full appearance-none rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white transition-colors focus:border-amber-500/50 focus:outline-none"
            >
              <option value="">—</option>
              {SUBJECTS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
              Message
            </label>
            <textarea
              required
              rows={6}
              value={form.message}
              onChange={(e) => setForm({ ...form, message: e.target.value })}
              className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white transition-colors placeholder:text-white/20 focus:border-amber-500/50 focus:outline-none resize-none"
            />
          </div>

          <button
            type="submit"
            disabled={sending}
            className="group flex w-full items-center justify-center gap-2 rounded-xl bg-amber-500 py-4 text-sm font-black uppercase tracking-wider text-black transition-all hover:bg-amber-400 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            {sending ? 'Sending...' : 'Send message'}
          </button>
        </form>
      )}

      <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-between rounded-2xl border border-white/5 bg-[#0A0A0A] p-6">
        <div className="flex items-center gap-3">
          <Clock className="h-4 w-4 text-white/30" />
          <span className="text-xs text-white/40">We typically respond within 24 hours</span>
        </div>
        <a
          href="mailto:2026@jobs-autoapply.com"
          className="flex items-center gap-2 text-xs font-bold text-amber-500 transition-colors hover:text-amber-400"
        >
          <Mail className="h-4 w-4" />
          2026@jobs-autoapply.com
        </a>
      </div>
    </div>
  )
}
