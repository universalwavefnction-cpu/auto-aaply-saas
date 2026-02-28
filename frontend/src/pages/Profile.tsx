import { useState, useEffect } from 'react'
import { UserCircle, Save, FileText, Upload, Trash2, KeyRound, Plus, MessageSquare, CheckCircle2 } from 'lucide-react'
import { api } from '../api'

function Field({ label, value, onChange, className = '', type = 'text' }: { label: string; value: string; onChange: (v: string) => void; className?: string; type?: string }) {
  return (
    <div className={className}>
      <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white transition-colors focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50" />
    </div>
  )
}

export default function Profile() {
  const [profile, setProfile] = useState<any>({})
  const [credentials, setCredentials] = useState<any[]>([])
  const [questions, setQuestions] = useState<Record<string, string>>({})
  const [newQ, setNewQ] = useState('')
  const [newA, setNewA] = useState('')
  const [newCred, setNewCred] = useState({ platform: 'stepstone', email: '', password: '' })
  const [saved, setSaved] = useState(false)
  const [cvs, setCvs] = useState<any[]>([])
  const [cvLabel, setCvLabel] = useState('')
  const [cvFile, setCvFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<{show: boolean, msg: string}>({ show: false, msg: '' })

  const showToast = (msg: string) => { setToast({ show: true, msg }); setTimeout(() => setToast({ show: false, msg: '' }), 3000) }

  useEffect(() => {
    Promise.all([
      api.getProfile().then((res) => { setProfile(res.profile || {}); setCredentials(res.credentials || []); setQuestions(res.profile?.questions_json || {}) }),
      api.listCVs().then((res) => { if (Array.isArray(res)) setCvs(res) })
    ]).finally(() => setLoading(false))
  }, [])

  const saveProfile = async () => { await api.updateProfile({ ...profile, questions_json: questions }); setSaved(true); showToast('Profile saved successfully'); setTimeout(() => setSaved(false), 2000) }
  const addQuestion = () => { if (newQ && newA) { setQuestions({ ...questions, [newQ.toLowerCase()]: newA }); setNewQ(''); setNewA(''); showToast('Q&A pair added') } }
  const removeQuestion = (key: string) => { const { [key]: _, ...rest } = questions; setQuestions(rest); showToast('Q&A pair removed') }

  if (loading) return (
    <div className="space-y-8 p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between"><div className="flex items-center gap-3"><div className="h-10 w-10 rounded-xl bg-white/5 shimmer"></div><div className="space-y-2"><div className="h-6 w-32 rounded bg-white/5 shimmer"></div><div className="h-3 w-24 rounded bg-white/5 shimmer"></div></div></div><div className="h-10 w-32 rounded-xl bg-white/5 shimmer"></div></div>
      <div className="grid gap-8 lg:grid-cols-12"><div className="space-y-8 lg:col-span-7"><div className="h-96 rounded-2xl bg-white/5 shimmer"></div></div><div className="space-y-8 lg:col-span-5"><div className="h-64 rounded-2xl bg-white/5 shimmer"></div><div className="h-64 rounded-2xl bg-white/5 shimmer"></div></div></div>
    </div>
  )

  return (
    <div className="space-y-8 p-8 max-w-5xl mx-auto relative">
      <div className={`fixed top-8 right-8 z-50 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm font-bold text-emerald-400 shadow-2xl backdrop-blur-md transition-all duration-300 ${toast.show ? 'translate-y-0 opacity-100' : '-translate-y-4 opacity-0 pointer-events-none'}`}><CheckCircle2 className="h-4 w-4" />{toast.msg}</div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20"><UserCircle className="h-5 w-5 text-amber-500" /></div>
          <div><h1 className="text-2xl font-bold tracking-tight text-white">Agent Profile</h1><p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">Identity & Assets</p></div>
        </div>
        <button onClick={saveProfile} className={`group relative flex items-center justify-center gap-2 overflow-hidden rounded-xl px-6 py-3 text-[10px] font-black uppercase tracking-wider transition-all ${saved ? 'bg-emerald-500 text-black' : 'bg-amber-500 text-black hover:bg-amber-400 active:scale-95'}`}><Save className="h-4 w-4" />{saved ? 'Saved Successfully' : 'Save Changes'}</button>
      </div>

      <div className="grid gap-8 lg:grid-cols-12">
        <div className="space-y-8 lg:col-span-7">
          <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] p-8 shadow-2xl transition-all hover:border-white/20">
            <div className="mb-6 flex items-center gap-3 border-b border-white/5 pb-4"><UserCircle className="h-5 w-5 text-white/40" /><h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">Personal Data</h2></div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <Field label="First Name" value={profile.first_name || ''} onChange={(v) => setProfile((p: any) => ({ ...p, first_name: v }))} />
              <Field label="Last Name" value={profile.last_name || ''} onChange={(v) => setProfile((p: any) => ({ ...p, last_name: v }))} />
              <Field label="Phone" value={profile.phone || ''} onChange={(v) => setProfile((p: any) => ({ ...p, phone: v }))} type="tel" />
              <Field label="City" value={profile.city || ''} onChange={(v) => setProfile((p: any) => ({ ...p, city: v }))} />
              <Field label="ZIP Code" value={profile.zip_code || ''} onChange={(v) => setProfile((p: any) => ({ ...p, zip_code: v }))} />
              <Field label="Street Address" value={profile.street_address || ''} onChange={(v) => setProfile((p: any) => ({ ...p, street_address: v }))} />
              <Field label="Expected Salary" value={String(profile.salary_expectation || '')} onChange={(v) => setProfile((p: any) => ({ ...p, salary_expectation: parseInt(v) || 0 }))} type="number" />
              <Field label="Experience (Years)" value={String(profile.years_experience || '')} onChange={(v) => setProfile((p: any) => ({ ...p, years_experience: parseInt(v) || 0 }))} type="number" />
            </div>
            <div className="mt-6">
              <label className="mb-2 block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Professional Summary</label>
              <textarea value={profile.summary || ''} onChange={(e) => setProfile((p: any) => ({ ...p, summary: e.target.value }))} rows={4} placeholder="A brief overview of your professional background..." className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white transition-colors placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50" />
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] p-8 shadow-2xl transition-all hover:border-white/20">
            <div className="mb-6 flex items-center justify-between border-b border-white/5 pb-4">
              <div className="flex items-center gap-3"><MessageSquare className="h-5 w-5 text-white/40" /><h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">Q&A Vault</h2></div>
              <span className="rounded-lg bg-white/5 px-3 py-1 text-[10px] font-bold text-white/40">{Object.keys(questions).length} pairs</span>
            </div>
            <div className="custom-scrollbar mb-6 max-h-[300px] space-y-2 overflow-auto pr-2">
              {Object.entries(questions).length === 0 ? (
                <div className="py-8 text-center"><MessageSquare className="mx-auto mb-3 h-8 w-8 text-white/10" /><p className="text-[10px] font-black uppercase tracking-wider text-white/30">No Q&A pairs added</p></div>
              ) : Object.entries(questions).map(([q, a]) => (
                <div key={q} className="group flex items-start gap-4 rounded-xl border border-white/5 bg-black/30 p-4 transition-colors hover:border-white/10">
                  <div className="min-w-0 flex-1 space-y-1"><p className="font-mono text-[11px] font-bold text-amber-500/80">Q: {q}</p><p className="text-sm text-white/80">A: {a}</p></div>
                  <button onClick={() => removeQuestion(q)} className="rounded-lg p-2 text-white/20 opacity-0 transition-all hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100"><Trash2 className="h-4 w-4" /></button>
                </div>
              ))}
            </div>
            <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-white/5">
              <input value={newQ} onChange={(e) => setNewQ(e.target.value)} placeholder="Question (e.g. Notice period?)" className="flex-1 rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50" />
              <input value={newA} onChange={(e) => setNewA(e.target.value)} placeholder="Answer (e.g. 4 weeks)" className="flex-1 rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50" />
              <button onClick={addQuestion} disabled={!newQ || !newA} className="flex items-center justify-center gap-2 rounded-xl bg-white/10 px-6 py-3 text-[10px] font-black uppercase tracking-wider text-white transition-colors hover:bg-white/20 disabled:opacity-30"><Plus className="h-4 w-4" /> Add</button>
            </div>
          </div>
        </div>

        <div className="space-y-8 lg:col-span-5">
          <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] p-8 shadow-2xl transition-all hover:border-white/20">
            <div className="mb-6 flex items-center justify-between border-b border-white/5 pb-4"><div className="flex items-center gap-3"><FileText className="h-5 w-5 text-white/40" /><h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">CV Library</h2></div><span className="rounded-lg bg-white/5 px-3 py-1 text-[10px] font-bold text-white/40">{cvs.length} files</span></div>
            <div className="mb-6 space-y-3">
              {cvs.length === 0 ? <div className="py-6 text-center"><p className="text-[10px] italic text-white/20">No CVs uploaded</p></div> : cvs.map((cv) => (
                <div key={cv.id} className="group flex items-center justify-between rounded-xl border border-white/5 bg-black/30 p-3 transition-colors hover:border-white/10">
                  <div className="flex items-center gap-3 overflow-hidden"><div className="rounded-lg bg-amber-500/10 p-2"><FileText className="h-4 w-4 text-amber-500" /></div><div className="min-w-0"><p className="truncate text-sm font-bold text-white/80">{cv.label}</p><p className="truncate text-[10px] text-white/40">{cv.filename}</p></div></div>
                  <button onClick={async () => { await api.deleteCV(cv.id); setCvs(cvs.filter((x: any) => x.id !== cv.id)); showToast('CV deleted') }} className="rounded-lg p-2 text-white/20 opacity-0 transition-all hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100"><Trash2 className="h-4 w-4" /></button>
                </div>
              ))}
            </div>
            <div className="space-y-3 rounded-xl border border-white/5 bg-black/30 p-4">
              <span className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Upload New CV</span>
              <input value={cvLabel} onChange={(e) => setCvLabel(e.target.value)} placeholder="Label (e.g. Management CV)" className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50" />
              <label className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-white/20 bg-white/5 px-4 py-3 transition-colors hover:border-amber-500/50 hover:bg-amber-500/5">
                <Upload className="h-4 w-4 shrink-0 text-white/40" /><span className="truncate text-sm text-white/60">{cvFile ? cvFile.name : 'Select PDF'}</span>
                <input type="file" accept=".pdf,.doc,.docx" className="hidden" onChange={(e) => setCvFile(e.target.files?.[0] || null)} />
              </label>
              <button onClick={async () => { if (!cvFile || !cvLabel.trim()) return; setUploading(true); const res = await api.uploadCV(cvFile, cvLabel.trim()); if (res && !res.error) { setCvs([res, ...cvs]); setCvLabel(''); setCvFile(null); showToast('CV uploaded') }; setUploading(false) }} disabled={!cvFile || !cvLabel.trim() || uploading} className="flex w-full items-center justify-center rounded-xl bg-amber-500 px-6 py-3 font-bold text-black transition-all hover:bg-amber-400 disabled:opacity-30">
                {uploading ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-black border-t-transparent" /> : 'Upload'}
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] p-8 shadow-2xl transition-all hover:border-white/20">
            <div className="mb-6 flex items-center justify-between border-b border-white/5 pb-4"><div className="flex items-center gap-3"><KeyRound className="h-5 w-5 text-white/40" /><h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">Platform Access</h2></div></div>
            <div className="mb-6 space-y-3">
              {credentials.length === 0 ? <div className="py-6 text-center"><p className="text-[10px] italic text-white/20">No credentials configured</p></div> : credentials.map((c) => (
                <div key={c.id} className="group flex items-center justify-between rounded-xl border border-white/5 bg-black/30 p-3 transition-colors hover:border-white/10">
                  <div className="flex items-center gap-3"><div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/5 text-[10px] font-black uppercase text-amber-500">{c.platform.substring(0, 2)}</div><div><p className="text-[10px] font-black uppercase tracking-wider text-white/60">{c.platform}</p><p className="text-xs text-white/40">{c.email}</p></div></div>
                  <button onClick={async () => { await api.deleteCredential(c.id); setCredentials(credentials.filter((x) => x.id !== c.id)); showToast('Credential removed') }} className="rounded-lg p-2 text-white/20 opacity-0 transition-all hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100"><Trash2 className="h-4 w-4" /></button>
                </div>
              ))}
            </div>
            <div className="space-y-3 rounded-xl border border-white/5 bg-black/30 p-4">
              <span className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Add Credential</span>
              <select value={newCred.platform} onChange={(e) => setNewCred({ ...newCred, platform: e.target.value })} className="w-full cursor-pointer appearance-none rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white transition-colors focus:border-amber-500/50 focus:bg-black focus:outline-none">
                <option value="stepstone">StepStone</option><option value="xing">Xing</option><option value="indeed">Indeed</option><option value="linkedin">LinkedIn</option>
              </select>
              <input value={newCred.email} onChange={(e) => setNewCred({ ...newCred, email: e.target.value })} placeholder="Email / Username" className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none" />
              <div className="flex gap-2">
                <input type="password" value={newCred.password} onChange={(e) => setNewCred({ ...newCred, password: e.target.value })} placeholder="Password" className="flex-1 rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none" />
                <button onClick={async () => { if (!newCred.email || !newCred.password) return; const res = await api.addCredential(newCred); if (res && !res.error) { setCredentials([...credentials, res]); setNewCred({ platform: 'stepstone', email: '', password: '' }); showToast('Credential added') } }} disabled={!newCred.email || !newCred.password} className="flex items-center justify-center rounded-xl bg-white/10 px-6 font-bold text-white transition-all hover:bg-white/20 disabled:opacity-30"><Plus className="h-5 w-5" /></button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
