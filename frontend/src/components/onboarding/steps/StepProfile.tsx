import { useState, useEffect, useRef } from 'react'
import { UserCircle, Save, CheckCircle2, AlertCircle } from 'lucide-react'
import { api } from '../../../api'

function Field({ label, value, onChange, type = 'text', placeholder = '', required = false }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string; required?: boolean
}) {
  return (
    <div>
      <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
        {label} {required && <span className="text-amber-500">*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white placeholder:text-white/20 transition-colors focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
      />
    </div>
  )
}

export default function StepProfile({ onComplete }: { onComplete: () => void }) {
  const [form, setForm] = useState({ first_name: '', last_name: '', phone: '', city: '', zip_code: '' })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete

  useEffect(() => {
    api.getProfile().then((res: any) => {
      const p = res.profile || {}
      const filled = {
        first_name: p.first_name || '',
        last_name: p.last_name || '',
        phone: p.phone || '',
        city: p.city || '',
        zip_code: p.zip_code || '',
      }
      setForm(filled)
      setLoaded(true)
      if (filled.first_name && filled.last_name && filled.phone && filled.city) {
        setSaved(true)
        onCompleteRef.current()
      }
    }).catch(() => setLoaded(true))
  }, [])

  const isValid = form.first_name.trim() && form.last_name.trim() && form.phone.trim() && form.city.trim()

  const handleSave = async () => {
    if (!isValid) return
    setSaving(true)
    setError(null)
    try {
      await api.updateProfile(form)
      setSaved(true)
      onComplete()
    } catch (e: any) {
      setError(e.message || 'Failed to save profile')
    } finally {
      setSaving(false)
    }
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
            <UserCircle className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Personal Information</h2>
            <p className="text-xs text-white/40">The bot uses this to fill application forms</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] p-6 sm:p-8 shadow-2xl fadeIn" style={{ animationDelay: '100ms', opacity: 0 }}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <Field label="First Name" value={form.first_name} onChange={(v) => { setForm((f) => ({ ...f, first_name: v })); setSaved(false) }} placeholder="Max" required />
          <Field label="Last Name" value={form.last_name} onChange={(v) => { setForm((f) => ({ ...f, last_name: v })); setSaved(false) }} placeholder="Mustermann" required />
          <Field label="Phone" value={form.phone} onChange={(v) => { setForm((f) => ({ ...f, phone: v })); setSaved(false) }} placeholder="+49 171 234 5678" type="tel" required />
          <Field label="City" value={form.city} onChange={(v) => { setForm((f) => ({ ...f, city: v })); setSaved(false) }} placeholder="Berlin" required />
          <Field label="ZIP Code" value={form.zip_code} onChange={(v) => { setForm((f) => ({ ...f, zip_code: v })); setSaved(false) }} placeholder="10115" />
        </div>

        {error && (
          <div className="mt-5 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <button
          onClick={handleSave}
          disabled={!isValid || saving || saved}
          className={`mt-6 flex w-full items-center justify-center gap-2 rounded-xl px-6 py-3.5 text-sm font-black uppercase tracking-wider transition-all ${
            saved
              ? 'bg-emerald-500 text-black'
              : 'bg-amber-500 text-black hover:bg-amber-400 active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed'
          }`}
        >
          {saving ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-black border-t-transparent" />
          ) : saved ? (
            <><CheckCircle2 className="h-4 w-4" /> Saved</>
          ) : (
            <><Save className="h-4 w-4" /> Save Profile</>
          )}
        </button>
      </div>
    </div>
  )
}
