import { useState, useEffect } from 'react'
import { api } from '../api'

function Field({
  label,
  value,
  onChange,
  className = '',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  className?: string
}) {
  return (
    <div className={className}>
      <label className="mb-2 block text-[8px] font-black uppercase tracking-[0.2em] text-white/15">
        {label}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-xl border border-white/5 bg-black px-4 py-2.5 text-sm text-white transition-colors focus:border-amber-500/30 focus:outline-none"
      />
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

  useEffect(() => {
    api.getProfile().then((res) => {
      setProfile(res.profile || {})
      setCredentials(res.credentials || [])
      setQuestions(res.profile?.questions_json || {})
    })
    api.listCVs().then((res) => {
      if (Array.isArray(res)) setCvs(res)
    })
  }, [])

  const saveProfile = async () => {
    await api.updateProfile({ ...profile, questions_json: questions })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const addQuestion = () => {
    if (newQ && newA) {
      setQuestions({ ...questions, [newQ.toLowerCase()]: newA })
      setNewQ('')
      setNewA('')
    }
  }

  const removeQuestion = (key: string) => {
    const { [key]: _, ...rest } = questions
    setQuestions(rest)
  }

  return (
    <div className="max-w-3xl space-y-6 p-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-amber-500/10 p-1.5">
            <svg
              className="h-4 w-4 text-amber-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                strokeLinecap="round"
                strokeWidth="2.5"
              />
            </svg>
          </div>
          <span className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">
            Agent Profile
          </span>
        </div>
        <button
          onClick={saveProfile}
          className="rounded-xl bg-amber-500 px-5 py-2.5 text-[10px] font-black uppercase tracking-wider text-white shadow-lg shadow-amber-500/20 transition-all hover:bg-amber-600"
        >
          {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>

      {/* Personal Info */}
      <div className="rounded-xl border border-white/5 bg-[#0A0A0A] p-6">
        <span className="mb-4 block text-[8px] font-black uppercase tracking-[0.2em] text-white/15">
          Personal Data
        </span>
        <div className="grid grid-cols-2 gap-4">
          <Field
            label="First Name"
            value={profile.first_name || ''}
            onChange={(v) => setProfile((p: any) => ({ ...p, first_name: v }))}
          />
          <Field
            label="Last Name"
            value={profile.last_name || ''}
            onChange={(v) => setProfile((p: any) => ({ ...p, last_name: v }))}
          />
          <Field
            label="Phone"
            value={profile.phone || ''}
            onChange={(v) => setProfile((p: any) => ({ ...p, phone: v }))}
          />
          <Field
            label="City"
            value={profile.city || ''}
            onChange={(v) => setProfile((p: any) => ({ ...p, city: v }))}
          />
          <Field
            label="ZIP"
            value={profile.zip_code || ''}
            onChange={(v) => setProfile((p: any) => ({ ...p, zip_code: v }))}
          />
          <Field
            label="Street"
            value={profile.street_address || ''}
            onChange={(v) => setProfile((p: any) => ({ ...p, street_address: v }))}
          />
          <Field
            label="Salary"
            value={String(profile.salary_expectation || '')}
            onChange={(v) =>
              setProfile((p: any) => ({ ...p, salary_expectation: parseInt(v) || 0 }))
            }
          />
          <Field
            label="Experience (yrs)"
            value={String(profile.years_experience || '')}
            onChange={(v) => setProfile((p: any) => ({ ...p, years_experience: parseInt(v) || 0 }))}
          />
        </div>
        <div className="mt-4">
          <label className="mb-2 block text-[8px] font-black uppercase tracking-[0.2em] text-white/15">
            Summary
          </label>
          <textarea
            value={profile.summary || ''}
            onChange={(e) => {
              const v = e.target.value
              setProfile((p: any) => ({ ...p, summary: v }))
            }}
            rows={3}
            className="w-full rounded-xl border border-white/5 bg-black px-4 py-2.5 text-sm text-white focus:border-amber-500/30 focus:outline-none"
          />
        </div>
      </div>

      {/* CV Library */}
      <div className="rounded-xl border border-white/5 bg-[#0A0A0A] p-6">
        <span className="mb-4 block text-[8px] font-black uppercase tracking-[0.2em] text-white/15">
          CV Library ({cvs.length} files)
        </span>
        <div className="mb-4 space-y-2">
          {cvs.map((cv) => (
            <div
              key={cv.id}
              className="flex items-center justify-between rounded-lg border border-white/5 bg-black px-3 py-2.5"
            >
              <div className="flex items-center gap-3">
                <span className="text-[9px] font-black uppercase tracking-wider text-amber-500">
                  PDF
                </span>
                <span className="text-sm text-white/60">{cv.label}</span>
                <span className="text-[10px] text-white/20">{cv.filename}</span>
              </div>
              <button
                onClick={async () => {
                  await api.deleteCV(cv.id)
                  setCvs(cvs.filter((x: any) => x.id !== cv.id))
                }}
                className="text-[9px] font-bold uppercase tracking-wider text-white/10 transition-colors hover:text-red-400"
              >
                Remove
              </button>
            </div>
          ))}
          {cvs.length === 0 && (
            <p className="px-3 text-[10px] italic text-white/10">
              No CVs uploaded — add one below to attach to applications
            </p>
          )}
        </div>
        <div className="border-t border-white/5 pt-4">
          <span className="mb-3 block text-[8px] font-black uppercase tracking-[0.2em] text-white/10">
            Upload CV
          </span>
          <div className="flex gap-2">
            <input
              value={cvLabel}
              onChange={(e) => setCvLabel(e.target.value)}
              placeholder="Label (e.g. Management CV)"
              className="w-48 rounded-xl border border-white/5 bg-black px-4 py-2.5 text-sm text-white placeholder:text-white/15 focus:border-amber-500/30 focus:outline-none"
            />
            <label className="flex flex-1 cursor-pointer items-center rounded-xl border border-white/5 bg-black px-4 py-2.5 transition-colors hover:border-white/10">
              <span className="truncate text-sm text-white/30">
                {cvFile ? cvFile.name : 'Choose PDF...'}
              </span>
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                className="hidden"
                onChange={(e) => setCvFile(e.target.files?.[0] || null)}
              />
            </label>
            <button
              onClick={async () => {
                if (!cvFile || !cvLabel.trim()) return
                setUploading(true)
                const res = await api.uploadCV(cvFile, cvLabel.trim())
                if (res && !res.error) {
                  setCvs([res, ...cvs])
                  setCvLabel('')
                  setCvFile(null)
                }
                setUploading(false)
              }}
              disabled={!cvFile || !cvLabel.trim() || uploading}
              className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-2.5 font-bold text-amber-500 transition-colors hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-30"
            >
              {uploading ? '...' : 'Upload'}
            </button>
          </div>
        </div>
      </div>

      {/* Q&A Database */}
      <div className="rounded-xl border border-white/5 bg-[#0A0A0A] p-6">
        <div className="mb-4 flex items-center justify-between">
          <span className="text-[8px] font-black uppercase tracking-[0.2em] text-white/15">
            Q&A Vault ({Object.keys(questions).length} pairs)
          </span>
        </div>
        <div className="custom-scrollbar mb-4 max-h-80 space-y-1 overflow-auto">
          {Object.entries(questions).map(([q, a]) => (
            <div
              key={q}
              className="group flex items-start gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-white/[0.02]"
            >
              <div className="min-w-0 flex-1 font-mono text-[11px]">
                <p className="truncate text-white/25">{q}</p>
                <p className="text-white/60">{a}</p>
              </div>
              <button
                onClick={() => removeQuestion(q)}
                className="mt-1 text-[10px] font-bold text-white/10 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
              >
                DEL
              </button>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            value={newQ}
            onChange={(e) => setNewQ(e.target.value)}
            placeholder="Question..."
            className="flex-1 rounded-xl border border-white/5 bg-black px-4 py-2.5 text-sm text-white placeholder:text-white/15 focus:border-amber-500/30 focus:outline-none"
          />
          <input
            value={newA}
            onChange={(e) => setNewA(e.target.value)}
            placeholder="Answer..."
            className="flex-1 rounded-xl border border-white/5 bg-black px-4 py-2.5 text-sm text-white placeholder:text-white/15 focus:border-amber-500/30 focus:outline-none"
          />
          <button
            onClick={addQuestion}
            className="rounded-xl border border-white/5 bg-white/5 px-4 py-2.5 font-bold text-white/40 transition-colors hover:text-amber-500"
          >
            +
          </button>
        </div>
      </div>

      {/* Credentials */}
      <div className="rounded-xl border border-white/5 bg-[#0A0A0A] p-6">
        <span className="mb-4 block text-[8px] font-black uppercase tracking-[0.2em] text-white/15">
          Platform Credentials
        </span>
        <div className="mb-4 space-y-2">
          {credentials.map((c) => (
            <div
              key={c.id}
              className="flex items-center justify-between rounded-lg border border-white/5 bg-black px-3 py-2.5"
            >
              <div className="flex items-center gap-3">
                <span className="text-[9px] font-black uppercase tracking-wider text-amber-500">
                  {c.platform}
                </span>
                <span className="text-[11px] text-white/30">{c.email}</span>
              </div>
              <button
                onClick={async () => {
                  await api.deleteCredential(c.id)
                  setCredentials(credentials.filter((x) => x.id !== c.id))
                }}
                className="text-[9px] font-bold uppercase tracking-wider text-white/10 transition-colors hover:text-red-400"
              >
                Remove
              </button>
            </div>
          ))}
          {credentials.length === 0 && (
            <p className="px-3 text-[10px] italic text-white/10">
              No credentials yet — add your StepStone or Xing login below
            </p>
          )}
        </div>
        <div className="border-t border-white/5 pt-4">
          <span className="mb-3 block text-[8px] font-black uppercase tracking-[0.2em] text-white/10">
            Add Credential
          </span>
          <div className="flex gap-2">
            <select
              value={newCred.platform}
              onChange={(e) => setNewCred({ ...newCred, platform: e.target.value })}
              className="cursor-pointer appearance-none rounded-xl border border-white/5 bg-black px-3 py-2.5 text-sm text-white focus:border-amber-500/30 focus:outline-none"
            >
              <option value="stepstone">StepStone</option>
              <option value="xing">Xing</option>
              <option value="indeed">Indeed</option>
              <option value="linkedin">LinkedIn</option>
            </select>
            <input
              value={newCred.email}
              onChange={(e) => setNewCred({ ...newCred, email: e.target.value })}
              placeholder="Email / Username"
              className="flex-1 rounded-xl border border-white/5 bg-black px-4 py-2.5 text-sm text-white placeholder:text-white/15 focus:border-amber-500/30 focus:outline-none"
            />
            <input
              type="password"
              value={newCred.password}
              onChange={(e) => setNewCred({ ...newCred, password: e.target.value })}
              placeholder="Password"
              className="flex-1 rounded-xl border border-white/5 bg-black px-4 py-2.5 text-sm text-white placeholder:text-white/15 focus:border-amber-500/30 focus:outline-none"
            />
            <button
              onClick={async () => {
                if (!newCred.email || !newCred.password) return
                const res = await api.addCredential(newCred)
                if (res && !res.error) {
                  setCredentials([...credentials, res])
                  setNewCred({ platform: 'stepstone', email: '', password: '' })
                }
              }}
              className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-2.5 font-bold text-amber-500 transition-colors hover:bg-amber-500/20"
            >
              + Add
            </button>
          </div>
        </div>
      </div>

      <style>{`.custom-scrollbar::-webkit-scrollbar{width:4px}.custom-scrollbar::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.05);border-radius:10px}`}</style>
    </div>
  )
}
