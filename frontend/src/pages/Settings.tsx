import { useState, useEffect } from 'react'
import { Settings, Save, Bot, Target, MapPin, Building2, AlertTriangle, Zap, CheckCircle2 } from 'lucide-react'
import { api } from '../api'

export default function SettingsPage() {
  const [filters, setFilters] = useState<any>({ job_titles: [], locations: [], remote_only: false, min_salary: 0, max_salary: 0, blacklist_companies: [], blacklist_keywords: [], autopilot_enabled: false })
  const [saved, setSaved] = useState(false)
  const [inputs, setInputs] = useState({ title: '', location: '', company: '', keyword: '' })
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<{show: boolean, msg: string}>({ show: false, msg: '' })

  const showToast = (msg: string) => { setToast({ show: true, msg }); setTimeout(() => setToast({ show: false, msg: '' }), 3000) }

  useEffect(() => { api.getFilters().then((f) => { if (f && !f.error) setFilters(f); setLoading(false) }) }, [])

  const save = async () => { await api.updateFilters(filters); setSaved(true); showToast('Configuration deployed successfully'); setTimeout(() => setSaved(false), 2000) }

  const addTo = (key: string, inputKey: string) => {
    const val = inputs[inputKey as keyof typeof inputs]
    if (val && !filters[key]?.includes(val)) { setFilters({ ...filters, [key]: [...(filters[key] || []), val] }); setInputs({ ...inputs, [inputKey]: '' }) }
  }
  const removeFrom = (key: string, val: string) => { setFilters({ ...filters, [key]: filters[key].filter((v: string) => v !== val) }) }

  const TagList = ({ title, icon: Icon, items, listKey, inputKey, placeholder }: { title: string; icon: any; items: string[]; listKey: string; inputKey: string; placeholder: string }) => (
    <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] p-8 shadow-2xl transition-all hover:border-white/20">
      <div className="mb-6 flex items-center gap-3 border-b border-white/5 pb-4"><Icon className="h-5 w-5 text-white/40" /><h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">{title}</h2></div>
      <div className="mb-6 flex flex-wrap gap-2 min-h-[40px]">
        {items.length === 0 ? <span className="flex items-center text-[10px] italic text-white/20">No items configured</span> : items.map((item) => (
          <span key={item} className="group flex items-center gap-2 rounded-lg border border-white/10 bg-black/50 px-3 py-1.5 text-xs font-bold text-white/80 transition-colors hover:border-amber-500/30 hover:bg-amber-500/5">
            {item}<button onClick={() => removeFrom(listKey, item)} className="text-white/20 transition-colors hover:text-red-400">&times;</button>
          </span>
        ))}
      </div>
      <div className="flex gap-3">
        <input value={inputs[inputKey as keyof typeof inputs]} onChange={(e) => setInputs({ ...inputs, [inputKey]: e.target.value })} onKeyDown={(e) => e.key === 'Enter' && addTo(listKey, inputKey)} placeholder={placeholder} className="flex-1 rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white transition-colors placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50" />
        <button onClick={() => addTo(listKey, inputKey)} disabled={!inputs[inputKey as keyof typeof inputs]} className="flex items-center justify-center rounded-xl bg-white/10 px-6 font-bold text-white transition-all hover:bg-white/20 disabled:opacity-30">Add</button>
      </div>
    </div>
  )

  if (loading) return (
    <div className="space-y-8 p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between"><div className="flex items-center gap-3"><div className="h-10 w-10 rounded-xl bg-white/5 shimmer"></div><div className="space-y-2"><div className="h-6 w-32 rounded bg-white/5 shimmer"></div><div className="h-3 w-24 rounded bg-white/5 shimmer"></div></div></div><div className="h-10 w-32 rounded-xl bg-white/5 shimmer"></div></div>
      <div className="h-32 rounded-2xl bg-white/5 shimmer"></div>
      <div className="grid gap-8 md:grid-cols-2"><div className="h-64 rounded-2xl bg-white/5 shimmer"></div><div className="h-64 rounded-2xl bg-white/5 shimmer"></div></div>
    </div>
  )

  return (
    <div className="space-y-8 p-8 max-w-4xl mx-auto relative">
      <div className={`fixed top-8 right-8 z-50 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm font-bold text-emerald-400 shadow-2xl backdrop-blur-md transition-all duration-300 ${toast.show ? 'translate-y-0 opacity-100' : '-translate-y-4 opacity-0 pointer-events-none'}`}><CheckCircle2 className="h-4 w-4" />{toast.msg}</div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20"><Settings className="h-5 w-5 text-amber-500" /></div>
          <div><h1 className="text-2xl font-bold tracking-tight text-white">Configuration</h1><p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">System Parameters</p></div>
        </div>
        <button onClick={save} className={`group relative flex items-center justify-center gap-2 overflow-hidden rounded-xl px-6 py-3 text-[10px] font-black uppercase tracking-wider transition-all ${saved ? 'bg-emerald-500 text-black' : 'bg-amber-500 text-black hover:bg-amber-400 active:scale-95'}`}>
          {saved ? <CheckCircle2 className="h-4 w-4" /> : <Save className="h-4 w-4" />}{saved ? 'Deployed Successfully' : 'Deploy Config'}
        </button>
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#0A0A0A] p-8 shadow-2xl transition-all hover:border-white/20">
        {filters.autopilot_enabled && <div className="absolute top-0 right-0 p-32 bg-amber-500/5 blur-[100px] rounded-full pointer-events-none"></div>}
        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className={`rounded-xl p-3 transition-colors ${filters.autopilot_enabled ? 'bg-amber-500/20 text-amber-500' : 'bg-white/5 text-white/40'}`}><Bot className="h-6 w-6" /></div>
            <div><h2 className="text-lg font-bold text-white">Autopilot Mode</h2><p className="mt-1 max-w-md text-sm text-white/40">When enabled, the agent will automatically scan platforms and apply to jobs matching your criteria on a schedule.</p></div>
          </div>
          <button onClick={() => setFilters({ ...filters, autopilot_enabled: !filters.autopilot_enabled })} className={`relative flex h-10 w-20 shrink-0 cursor-pointer items-center rounded-full p-1 transition-colors duration-300 focus:outline-none ${filters.autopilot_enabled ? 'bg-amber-500 shadow-[0_0_20px_rgba(245,158,11,0.4)]' : 'bg-white/10'}`}>
            <div className={`h-8 w-8 rounded-full bg-white shadow-md transition-transform duration-300 ${filters.autopilot_enabled ? 'translate-x-10' : 'translate-x-0'}`} />
          </button>
        </div>
        <div className={`transition-all duration-300 overflow-hidden ${filters.autopilot_enabled ? 'max-h-24 opacity-100 mt-6' : 'max-h-0 opacity-0 mt-0'}`}>
          <div className="flex items-center gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3"><Zap className="h-4 w-4 text-amber-500" /><span className="text-[10px] font-black uppercase tracking-wider text-amber-500">System will autonomously execute applications based on configured parameters below</span></div>
        </div>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <TagList title="Target Job Titles" icon={Target} items={filters.job_titles || []} listKey="job_titles" inputKey="title" placeholder="e.g. Frontend Developer" />
        <TagList title="Target Locations" icon={MapPin} items={filters.locations || []} listKey="locations" inputKey="location" placeholder="e.g. Berlin, Remote" />
      </div>

      <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] p-8 shadow-2xl transition-all hover:border-white/20">
        <div className="mb-6 flex items-center gap-3 border-b border-white/5 pb-4"><Settings className="h-5 w-5 text-white/40" /><h2 className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">Preferences & Constraints</h2></div>
        <div className="grid gap-8 sm:grid-cols-2">
          <div className="space-y-4"><label className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Minimum Salary</label><input type="number" value={filters.min_salary || ''} onChange={(e) => setFilters({ ...filters, min_salary: parseInt(e.target.value) || 0 })} placeholder="e.g. 60000" className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white transition-colors focus:border-amber-500/50 focus:bg-black focus:outline-none" /></div>
          <div className="space-y-4"><label className="block text-[9px] font-black uppercase tracking-[0.2em] text-white/40">Maximum Salary</label><input type="number" value={filters.max_salary || ''} onChange={(e) => setFilters({ ...filters, max_salary: parseInt(e.target.value) || 0 })} placeholder="e.g. 120000" className="w-full rounded-xl border border-white/10 bg-black/50 px-4 py-3 text-sm text-white transition-colors focus:border-amber-500/50 focus:bg-black focus:outline-none" /></div>
        </div>
        <div className="mt-8 flex items-center gap-4 border-t border-white/5 pt-6">
          <button onClick={() => setFilters({ ...filters, remote_only: !filters.remote_only })} className={`relative flex h-6 w-12 shrink-0 cursor-pointer items-center rounded-full p-1 transition-colors duration-300 focus:outline-none ${filters.remote_only ? 'bg-amber-500' : 'bg-white/10'}`}>
            <div className={`h-4 w-4 rounded-full bg-white shadow-md transition-transform duration-300 ${filters.remote_only ? 'translate-x-6' : 'translate-x-0'}`} />
          </button>
          <div><span className="text-sm font-bold text-white">Remote Only</span><p className="text-[10px] text-white/40">Only apply to positions explicitly marked as remote</p></div>
        </div>
      </div>

      <div className="grid gap-8 md:grid-cols-2">
        <TagList title="Blacklisted Companies" icon={Building2} items={filters.blacklist_companies || []} listKey="blacklist_companies" inputKey="company" placeholder="e.g. Amazon, Meta" />
        <TagList title="Blacklisted Keywords" icon={AlertTriangle} items={filters.blacklist_keywords || []} listKey="blacklist_keywords" inputKey="keyword" placeholder="e.g. Blockchain, Crypto" />
      </div>
    </div>
  )
}
