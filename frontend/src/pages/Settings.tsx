import { useState, useEffect } from 'react'
import { api } from '../api'

export default function SettingsPage() {
  const [filters, setFilters] = useState<any>({
    job_titles: [], locations: [], remote_only: false,
    min_salary: 0, max_salary: 0,
    blacklist_companies: [], blacklist_keywords: [],
    autopilot_enabled: false,
  })
  const [saved, setSaved] = useState(false)
  const [inputs, setInputs] = useState({ title: '', location: '', company: '', keyword: '' })

  useEffect(() => {
    api.getFilters().then(f => { if (f && !f.error) setFilters(f) })
  }, [])

  const save = async () => {
    await api.updateFilters(filters)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const addTo = (key: string, inputKey: string) => {
    const val = inputs[inputKey as keyof typeof inputs]
    if (val && !filters[key]?.includes(val)) {
      setFilters({ ...filters, [key]: [...(filters[key] || []), val] })
      setInputs({ ...inputs, [inputKey]: '' })
    }
  }

  const removeFrom = (key: string, val: string) => {
    setFilters({ ...filters, [key]: filters[key].filter((v: string) => v !== val) })
  }

  const TagList = ({ title, items, listKey, inputKey, placeholder }: {
    title: string; items: string[]; listKey: string; inputKey: string; placeholder: string
  }) => (
    <div className="bg-[#0A0A0A] border border-white/5 rounded-xl p-6">
      <span className="text-[8px] font-black text-white/15 uppercase tracking-[0.2em] block mb-3">{title}</span>
      <div className="flex flex-wrap gap-2 mb-3">
        {items.map(item => (
          <span key={item} className="flex items-center gap-2 px-3 py-1.5 bg-black border border-white/5 rounded-lg text-[10px] font-bold text-white/50">
            {item}
            <button onClick={() => removeFrom(listKey, item)} className="text-white/15 hover:text-red-400 transition-colors">x</button>
          </span>
        ))}
        {items.length === 0 && <span className="text-[10px] text-white/10 italic">None configured</span>}
      </div>
      <div className="flex gap-2">
        <input
          value={inputs[inputKey as keyof typeof inputs]}
          onChange={e => setInputs({ ...inputs, [inputKey]: e.target.value })}
          onKeyDown={e => e.key === 'Enter' && addTo(listKey, inputKey)}
          placeholder={placeholder}
          className="flex-1 px-4 py-2.5 bg-black border border-white/5 rounded-xl text-sm text-white placeholder:text-white/15 focus:outline-none focus:border-amber-500/30"
        />
        <button onClick={() => addTo(listKey, inputKey)}
          className="px-4 py-2.5 bg-white/5 border border-white/5 rounded-xl text-white/40 hover:text-amber-500 font-bold transition-colors">+</button>
      </div>
    </div>
  )

  return (
    <div className="p-8 max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-amber-500/10 rounded-md">
            <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.573-1.066z" strokeLinecap="round" strokeWidth="2"/>
              <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" strokeLinecap="round" strokeWidth="2"/>
            </svg>
          </div>
          <span className="uppercase font-black tracking-[0.2em] text-[11px] text-white/60">Configuration</span>
        </div>
        <button onClick={save}
          className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-[10px] font-black uppercase tracking-wider shadow-lg shadow-amber-500/20 transition-all">
          {saved ? 'Deployed!' : 'Deploy Config'}
        </button>
      </div>

      {/* Autopilot Toggle */}
      <div className="bg-[#0A0A0A] border border-white/5 rounded-xl p-6">
        <div className="flex items-center justify-between">
          <div>
            <span className="font-bold text-sm text-white/80">Autopilot Mode</span>
            <p className="text-[10px] text-white/20 mt-1">Automatically apply to matching targets</p>
          </div>
          <button
            onClick={() => setFilters({ ...filters, autopilot_enabled: !filters.autopilot_enabled })}
            className={`w-14 h-7 rounded-full transition-all relative ${
              filters.autopilot_enabled ? 'bg-amber-500 shadow-lg shadow-amber-500/30' : 'bg-white/10'
            }`}
          >
            <div className={`w-5 h-5 rounded-full bg-white absolute top-1 transition-all ${
              filters.autopilot_enabled ? 'left-8' : 'left-1'
            }`} />
          </button>
        </div>
        {filters.autopilot_enabled && (
          <div className="mt-4 flex items-center gap-2 px-3 py-2 bg-amber-500/5 border border-amber-500/20 rounded-lg">
            <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></div>
            <span className="text-[9px] font-black text-amber-500 uppercase tracking-wider">Autopilot Active — Agent will apply automatically</span>
          </div>
        )}
      </div>

      <TagList title="Target Job Titles" items={filters.job_titles || []} listKey="job_titles" inputKey="title" placeholder="e.g. Project Manager" />
      <TagList title="Target Locations" items={filters.locations || []} listKey="locations" inputKey="location" placeholder="e.g. Berlin" />

      {/* Salary */}
      <div className="bg-[#0A0A0A] border border-white/5 rounded-xl p-6">
        <span className="text-[8px] font-black text-white/15 uppercase tracking-[0.2em] block mb-3">Salary Range</span>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[8px] font-black text-white/10 uppercase tracking-[0.2em] block mb-2">Minimum</label>
            <input type="number" value={filters.min_salary || ''}
              onChange={e => setFilters({ ...filters, min_salary: parseInt(e.target.value) || 0 })}
              className="w-full px-4 py-2.5 bg-black border border-white/5 rounded-xl text-sm text-white focus:outline-none focus:border-amber-500/30" />
          </div>
          <div>
            <label className="text-[8px] font-black text-white/10 uppercase tracking-[0.2em] block mb-2">Maximum</label>
            <input type="number" value={filters.max_salary || ''}
              onChange={e => setFilters({ ...filters, max_salary: parseInt(e.target.value) || 0 })}
              className="w-full px-4 py-2.5 bg-black border border-white/5 rounded-xl text-sm text-white focus:outline-none focus:border-amber-500/30" />
          </div>
        </div>
        <label className="flex items-center gap-3 mt-4 text-[10px] text-white/30 font-bold cursor-pointer">
          <input type="checkbox" checked={filters.remote_only}
            onChange={e => setFilters({ ...filters, remote_only: e.target.checked })}
            className="rounded border-white/10" />
          Remote Only
        </label>
      </div>

      <TagList title="Blacklisted Companies" items={filters.blacklist_companies || []} listKey="blacklist_companies" inputKey="company" placeholder="Company to skip" />
      <TagList title="Blacklisted Keywords" items={filters.blacklist_keywords || []} listKey="blacklist_keywords" inputKey="keyword" placeholder="Keyword to skip" />
    </div>
  )
}
