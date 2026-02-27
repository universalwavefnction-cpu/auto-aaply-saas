import { useState } from 'react'
import { api } from '../api'

export default function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isRegister, setIsRegister] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
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
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#050505]">
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-500/5 blur-[120px]"></div>

      <div className="relative z-10 w-full max-w-sm">
        <div className="mb-10 text-center">
          <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500 shadow-xl shadow-amber-500/20">
            <svg
              className="h-8 w-8 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-black tracking-tight text-white">AutoApply</h1>
          <p className="mt-1 text-[10px] font-black uppercase tracking-[0.3em] text-amber-500">
            Intelligence
          </p>
        </div>

        <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-8">
          <h2 className="mb-6 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
            {isRegister ? 'Create Account' : 'Authenticate'}
          </h2>

          {error && (
            <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">
              <p className="text-[11px] font-bold text-red-400">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/20">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-black px-4 py-3 text-sm text-white transition-colors focus:border-amber-500/50 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/20">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-black px-4 py-3 text-sm text-white transition-colors focus:border-amber-500/50 focus:outline-none"
                required
              />
            </div>
            <button
              type="submit"
              className="w-full rounded-xl bg-amber-500 py-3 text-sm font-black text-white shadow-lg shadow-amber-500/20 transition-all hover:scale-[1.02] hover:bg-amber-600 active:scale-100"
            >
              {isRegister ? 'Initialize Agent' : 'Launch Mission'}
            </button>
          </form>

          <p className="mt-6 text-center text-[10px] font-bold text-white/20">
            {isRegister ? 'Already registered?' : 'New operator?'}{' '}
            <button
              onClick={() => setIsRegister(!isRegister)}
              className="text-amber-500 hover:underline"
            >
              {isRegister ? 'Authenticate' : 'Register'}
            </button>
          </p>
        </div>

        <div className="mt-8 flex items-center justify-center gap-2">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#27C93F]"></div>
          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-[#27C93F]/60">
            All Systems Operational
          </span>
        </div>
      </div>
    </div>
  )
}
