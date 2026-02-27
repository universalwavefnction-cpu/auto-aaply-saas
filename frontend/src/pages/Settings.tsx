import { useState, useEffect } from 'react'
import { api } from '../api'

export default function SettingsPage() {
  const [filters, setFilters] = useState<any>({
    job_titles: [],
    locations: [],
    remote_only: false,
    min_salary: 0,
    max_salary: 0,
    blacklist_companies: [],
    blacklist_keywords: [],
    autopilot_enabled: false,
  })
  const [saved, setSaved] = useState(false)
  const [inputs, setInputs] = useState({ title: '', location: '', company: '', keyword: '' })

  useEffect(() => {
    api.getFilters().then((f) => {
      if (f && !f.error) setFilters(f)
    })
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

  const TagList = ({
    title,
    items,
    listKey,
    inputKey,
    placeholder,
  }: {
    title: string
    items: string[]
    listKey: string
    inputKey: string
    placeholder: string
  }) => (
    <div className="rounded-xl border border-white/5 bg-[#0A0A0A] p-6">
      <span className="mb-3 block text-[8px] font-black uppercase tracking-[0.2em] text-white/15">
        {title}
      </span>
      <div className="mb-3 flex flex-wrap gap-2">
        {items.map((item) => (
          <span
            key={item}
            className="flex items-center gap-2 rounded-lg border border-white/5 bg-black px-3 py-1.5 text-[10px] font-bold text-white/50"
          >
            {item}
            <button
              onClick={() => removeFrom(listKey, item)}
              className="text-white/15 transition-colors hover:text-red-400"
            >
              x
            </button>
          </span>
        ))}
        {items.length === 0 && (
          <span className="text-[10px] italic text-white/10">None configured</span>
        )}
      </div>
      <div className="flex gap-2">
        <input
          value={inputs[inputKey as keyof typeof inputs]}
          onChange={(e) => setInputs({ ...inputs, [inputKey]: e.target.value })}
          onKeyDown={(e) => e.key === 'Enter' && addTo(listKey, inputKey)}
          placeholder={placeholder}
          className="flex-1 rounded-xl border border-white/5 bg-black px-4 py-2.5 text-sm text-white placeholder:text-white/15 focus:border-amber-500/30 focus:outline-none"
        />
        <button
          onClick={() => addTo(listKey, inputKey)}
          className="rounded-xl border border-white/5 bg-white/5 px-4 py-2.5 font-bold text-white/40 transition-colors hover:text-amber-500"
        >
          +
        </button>
      </div>
    </div>
  )

  return (
    <div className="max-w-2xl space-y-6 p-8">
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
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.573-1.066z"
                strokeLinecap="round"
                strokeWidth="2"
              />
              <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" strokeLinecap="round" strokeWidth="2" />
            </svg>
          </div>
          <span className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">
            Configuration
          </span>
        </div>
        <button
          onClick={save}
          className="rounded-xl bg-amber-500 px-5 py-2.5 text-[10px] font-black uppercase tracking-wider text-white shadow-lg shadow-amber-500/20 transition-all hover:bg-amber-600"
        >
          {saved ? 'Deployed!' : 'Deploy Config'}
        </button>
      </div>

      {/* Autopilot Toggle */}
      <div className="rounded-xl border border-white/5 bg-[#0A0A0A] p-6">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-sm font-bold text-white/80">Autopilot Mode</span>
            <p className="mt-1 text-[10px] text-white/20">
              Automatically apply to matching targets
            </p>
          </div>
          <button
            onClick={() =>
              setFilters({ ...filters, autopilot_enabled: !filters.autopilot_enabled })
            }
            className={`relative h-7 w-14 rounded-full transition-all ${
              filters.autopilot_enabled
                ? 'bg-amber-500 shadow-lg shadow-amber-500/30'
                : 'bg-white/10'
            }`}
          >
            <div
              className={`absolute top-1 h-5 w-5 rounded-full bg-white transition-all ${
                filters.autopilot_enabled ? 'left-8' : 'left-1'
              }`}
            />
          </button>
        </div>
        {filters.autopilot_enabled && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2">
            <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500"></div>
            <span className="text-[9px] font-black uppercase tracking-wider text-amber-500">
              Autopilot Active — Agent will apply automatically
            </span>
          </div>
        )}
      </div>

      <TagList
        title="Target Job Titles"
        items={filters.job_titles || []}
        listKey="job_titles"
        inputKey="title"
        placeholder="e.g. Project Manager"
      />
      <TagList
        title="Target Locations"
        items={filters.locations || []}
        listKey="locations"
        inputKey="location"
        placeholder="e.g. Berlin"
      />

      {/* Salary */}
      <div className="rounded-xl border border-white/5 bg-[#0A0A0A] p-6">
        <span className="mb-3 block text-[8px] font-black uppercase tracking-[0.2em] text-white/15">
          Salary Range
        </span>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-2 block text-[8px] font-black uppercase tracking-[0.2em] text-white/10">
              Minimum
            </label>
            <input
              type="number"
              value={filters.min_salary || ''}
              onChange={(e) =>
                setFilters({ ...filters, min_salary: parseInt(e.target.value) || 0 })
              }
              className="w-full rounded-xl border border-white/5 bg-black px-4 py-2.5 text-sm text-white focus:border-amber-500/30 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-2 block text-[8px] font-black uppercase tracking-[0.2em] text-white/10">
              Maximum
            </label>
            <input
              type="number"
              value={filters.max_salary || ''}
              onChange={(e) =>
                setFilters({ ...filters, max_salary: parseInt(e.target.value) || 0 })
              }
              className="w-full rounded-xl border border-white/5 bg-black px-4 py-2.5 text-sm text-white focus:border-amber-500/30 focus:outline-none"
            />
          </div>
        </div>
        <label className="mt-4 flex cursor-pointer items-center gap-3 text-[10px] font-bold text-white/30">
          <input
            type="checkbox"
            checked={filters.remote_only}
            onChange={(e) => setFilters({ ...filters, remote_only: e.target.checked })}
            className="rounded border-white/10"
          />
          Remote Only
        </label>
      </div>

      <TagList
        title="Blacklisted Companies"
        items={filters.blacklist_companies || []}
        listKey="blacklist_companies"
        inputKey="company"
        placeholder="Company to skip"
      />
      <TagList
        title="Blacklisted Keywords"
        items={filters.blacklist_keywords || []}
        listKey="blacklist_keywords"
        inputKey="keyword"
        placeholder="Keyword to skip"
      />
    </div>
  )
}
