import React, { useState } from 'react'
import { Sparkles, Lock, Mail, ArrowRight, UserPlus, LogIn } from 'lucide-react'
import { api } from '../api'

export default function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isRegister, setIsRegister] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = isRegister
        ? await api.register(email, password)
        : await api.login(email, password)
      if (res.access_token) {
        onLogin(res.access_token)
      } else {
        setError(res.detail || 'Authentication failed')
      }
    } catch (err: any) {
      setError(err.message || 'Connection error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050505] selection:bg-amber-500/30">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-amber-500/5 via-[#050505] to-[#050505]"></div>
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[800px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-500/5 blur-[120px] animate-pulse" />

      <div className="relative z-10 w-full max-w-md px-6">
        <div className="mb-12 text-center fadeIn">
          <div className="mx-auto mb-8 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 shadow-[0_0_40px_rgba(245,158,11,0.3)]">
            <Sparkles className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-4xl font-black tracking-tight text-white">AutoApply</h1>
          <p className="mt-2 text-[11px] font-black uppercase tracking-[0.4em] text-amber-500">Intelligence</p>
        </div>

        <div className="overflow-hidden rounded-3xl border border-white/10 bg-[#0A0A0A]/80 p-8 shadow-2xl backdrop-blur-xl fadeIn" style={{ animationDelay: '100ms' }}>
          <div className="mb-8 flex items-center justify-between border-b border-white/5 pb-6">
            <h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">
              {isRegister ? 'Initialize Agent' : 'Authenticate'}
            </h2>
            <div className="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-1.5">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
              <span className="text-[9px] font-bold uppercase tracking-widest text-emerald-500">System Online</span>
            </div>
          </div>

          <div className={`transition-all duration-300 overflow-hidden ${error ? 'max-h-24 opacity-100 mb-6' : 'max-h-0 opacity-0 mb-0'}`}>
            <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
              <p className="text-[11px] font-bold text-red-400">{error}</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                <Mail className="h-3 w-3" /> Email Designation
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3.5 text-sm text-white transition-all placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                placeholder="operator@autoapply.ai"
                required
              />
            </div>

            <div className="space-y-2">
              <label className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                <Lock className="h-3 w-3" /> Security Clearance
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3.5 text-sm text-white transition-all placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading || !email || !password}
              className="group relative mt-8 flex w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-amber-500 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_20px_rgba(245,158,11,0.2)] transition-all hover:scale-[1.02] hover:bg-amber-400 hover:shadow-[0_0_30px_rgba(245,158,11,0.4)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
            >
              <div className="absolute inset-0 flex h-full w-full justify-center [transform:skew(-12deg)_translateX(-100%)] group-hover:duration-1000 group-hover:[transform:skew(-12deg)_translateX(100%)]">
                <div className="relative h-full w-8 bg-white/20" />
              </div>
              <span className="relative flex items-center gap-2">
                {loading ? (
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-black border-t-transparent" />
                ) : (
                  <>
                    {isRegister ? 'Initialize Agent' : 'Launch Mission'}
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </span>
            </button>
          </form>

          <div className="mt-8 border-t border-white/5 pt-6 text-center">
            <p className="text-[11px] font-bold text-white/40">
              {isRegister ? 'Already registered?' : 'New operator?'}{' '}
              <button
                type="button"
                onClick={() => setIsRegister(!isRegister)}
                className="inline-flex items-center gap-1 text-amber-500 transition-colors hover:text-amber-400 hover:underline"
              >
                {isRegister ? <><LogIn className="h-3 w-3" /> Authenticate</> : <><UserPlus className="h-3 w-3" /> Register</>}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
