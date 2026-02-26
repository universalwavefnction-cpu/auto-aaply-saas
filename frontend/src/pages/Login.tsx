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
    <div className="min-h-screen flex items-center justify-center bg-[#050505] relative overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-amber-500/5 rounded-full blur-[120px] pointer-events-none"></div>

      <div className="w-full max-w-sm relative z-10">
        <div className="text-center mb-10">
          <div className="w-14 h-14 bg-amber-500 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-xl shadow-amber-500/20">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="text-3xl font-black tracking-tight text-white">AutoApply</h1>
          <p className="text-[10px] text-amber-500 font-black uppercase tracking-[0.3em] mt-1">Intelligence</p>
        </div>

        <div className="bg-[#0A0A0A] rounded-2xl p-8 border border-white/5">
          <h2 className="text-white/40 text-[10px] font-black uppercase tracking-[0.2em] mb-6">
            {isRegister ? 'Create Account' : 'Authenticate'}
          </h2>

          {error && (
            <div className="mb-4 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg">
              <p className="text-red-400 text-[11px] font-bold">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-[9px] font-black text-white/20 uppercase tracking-[0.2em] block mb-2">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-black border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-amber-500/50 transition-colors"
                required
              />
            </div>
            <div>
              <label className="text-[9px] font-black text-white/20 uppercase tracking-[0.2em] block mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-black border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-amber-500/50 transition-colors"
                required
              />
            </div>
            <button
              type="submit"
              className="w-full py-3 bg-amber-500 hover:bg-amber-600 text-white rounded-xl font-black text-sm shadow-lg shadow-amber-500/20 transition-all hover:scale-[1.02] active:scale-100"
            >
              {isRegister ? 'Initialize Agent' : 'Launch Mission'}
            </button>
          </form>

          <p className="text-center text-white/20 text-[10px] font-bold mt-6">
            {isRegister ? 'Already registered?' : 'New operator?'}{' '}
            <button onClick={() => setIsRegister(!isRegister)} className="text-amber-500 hover:underline">
              {isRegister ? 'Authenticate' : 'Register'}
            </button>
          </p>
        </div>

        <div className="flex items-center justify-center gap-2 mt-8">
          <div className="w-1.5 h-1.5 rounded-full bg-[#27C93F] animate-pulse"></div>
          <span className="text-[9px] font-black text-[#27C93F]/60 uppercase tracking-[0.2em]">All Systems Operational</span>
        </div>
      </div>
    </div>
  )
}
