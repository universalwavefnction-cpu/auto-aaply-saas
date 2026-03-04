import { useState, useEffect, useRef } from 'react'
import { KeyRound, Plus, CheckCircle2, AlertCircle, Trash2, Shield, AlertTriangle } from 'lucide-react'
import { api } from '../../../api'

const platforms = [
  { value: 'xing', label: 'Xing', short: 'XI' },
  { value: 'stepstone', label: 'StepStone', short: 'SS' },
  { value: 'linkedin', label: 'LinkedIn', short: 'LI' },
]

export default function StepCredentials({ onComplete }: { onComplete: () => void }) {
  const [credentials, setCredentials] = useState<any[]>([])
  const [cred, setCred] = useState({ platform: 'xing', email: '', password: '', gmail_email: '', gmail_app_password: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete

  useEffect(() => {
    api.getProfile().then((res: any) => {
      const creds = res.credentials || []
      setCredentials(creds)
      setLoaded(true)
      if (creds.length > 0) onCompleteRef.current()
    }).catch(() => setLoaded(true))
  }, [])

  const handleAdd = async () => {
    if (!cred.email || !cred.password) return
    setSaving(true)
    setError(null)
    try {
      const res = await api.addCredential(cred)
      if (res && !res.error) {
        setCredentials((prev) => [...prev, res])
        setCred({ platform: 'xing', email: '', password: '', gmail_email: '', gmail_app_password: '' })
        onComplete()
      } else {
        setError(res?.error || res?.detail || 'Failed to add credential')
      }
    } catch (e: any) {
      setError(e.message || 'Failed to add credential')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    await api.deleteCredential(id)
    setCredentials((prev) => prev.filter((c) => c.id !== id))
  }

  if (!loaded) return (
    <div className="flex items-center justify-center min-h-full">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
    </div>
  )

  return (
    <div className="p-4 sm:p-6 md:p-8 max-w-xl mx-auto">
      <div className="fadeIn" style={{ animationDelay: '0ms', opacity: 0 }}>
        <div className="flex items-center gap-3 mb-6">
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
            <KeyRound className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Platform Credentials</h2>
            <p className="text-xs text-white/40">Add your login for at least one job platform</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] p-6 sm:p-8 shadow-2xl fadeIn" style={{ animationDelay: '100ms', opacity: 0 }}>
        {/* Existing credentials */}
        {credentials.length > 0 && (
          <div className="mb-6 space-y-3">
            <span className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Connected Platforms</span>
            {credentials.map((c) => (
              <div key={c.id} className="group rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-[10px] font-black uppercase text-emerald-400">
                      {c.platform.substring(0, 2)}
                    </div>
                    <div>
                      <p className="text-[10px] font-black uppercase tracking-wider text-white/60">{c.platform}</p>
                      <p className="text-xs text-white/40">{c.email}</p>
                    </div>
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 ml-2" />
                  </div>
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="rounded-lg p-2 text-white/20 opacity-0 transition-all hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                {c.platform === 'linkedin' && !c.has_gmail_app_password && (
                  <div className="mt-2 flex items-center gap-2 pl-11">
                    <AlertTriangle className="h-3 w-3 text-red-400/60" />
                    <span className="text-[9px] font-bold text-red-400/60">Email verification not configured</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Platform selector */}
        <div className="mb-4">
          <span className="block mb-2 text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Platform</span>
          <div className="flex gap-2">
            {platforms.map((p) => (
              <button
                key={p.value}
                onClick={() => setCred((c) => ({ ...c, platform: p.value }))}
                className={`flex-1 rounded-xl border px-4 py-3 text-xs font-black uppercase tracking-wider transition-all ${
                  cred.platform === p.value
                    ? 'border-amber-500/50 bg-amber-500/10 text-amber-500'
                    : 'border-white/10 bg-black/30 text-white/40 hover:border-white/20'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Credential fields */}
        <div className="space-y-3">
          <div>
            <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
              Email / Username <span className="text-amber-500">*</span>
            </label>
            <input
              value={cred.email}
              onChange={(e) => setCred((c) => ({ ...c, email: e.target.value }))}
              placeholder="your@email.com"
              className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            />
          </div>
          <div>
            <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
              Password <span className="text-amber-500">*</span>
            </label>
            <input
              type="password"
              value={cred.password}
              onChange={(e) => setCred((c) => ({ ...c, password: e.target.value }))}
              placeholder="••••••••"
              className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            />
          </div>
        </div>

        {/* LinkedIn extra fields */}
        {cred.platform === 'linkedin' && (
          <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 space-y-3">
            <div className="flex items-start gap-2">
              <Shield className="h-4 w-4 shrink-0 mt-0.5 text-amber-500" />
              <div>
                <p className="text-xs font-bold text-amber-400">LinkedIn requires email verification</p>
                <p className="mt-1 text-[11px] leading-relaxed text-white/50">
                  LinkedIn sends a code via email when the bot logs in. Provide your Gmail App Password so the bot can read it automatically.
                </p>
              </div>
            </div>
            <input
              value={cred.gmail_email}
              onChange={(e) => setCred((c) => ({ ...c, gmail_email: e.target.value }))}
              placeholder="Gmail address (e.g. you@gmail.com)"
              className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none"
            />
            <input
              value={cred.gmail_app_password}
              onChange={(e) => setCred((c) => ({ ...c, gmail_app_password: e.target.value }))}
              placeholder="Gmail App Password (16 characters)"
              className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm font-mono text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none"
            />
            <p className="text-[10px] text-white/30">
              Optional — you can set this up later in Profile → Platform Access
            </p>
          </div>
        )}

        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <button
          onClick={handleAdd}
          disabled={!cred.email || !cred.password || saving}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-amber-500 px-6 py-3.5 text-sm font-black uppercase tracking-wider text-black transition-all hover:bg-amber-400 active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {saving ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-black border-t-transparent" />
          ) : (
            <><Plus className="h-4 w-4" /> Add Credential</>
          )}
        </button>
      </div>
    </div>
  )
}
