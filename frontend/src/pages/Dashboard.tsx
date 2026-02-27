import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)
  const [jobTitle, setJobTitle] = useState('')
  const [location, setLocation] = useState('')
  const [platform, setPlatform] = useState('stepstone')
  const [maxApps, setMaxApps] = useState(10)
  const [selectedCv, setSelectedCv] = useState<number | null>(null)
  const [cvs, setCvs] = useState<any[]>([])
  const [launching, setLaunching] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.getStats().then(setStats)
    api.listCVs().then((res) => {
      if (Array.isArray(res)) setCvs(res)
    })
    // Pre-fill from saved filters
    api.getFilters().then((f) => {
      if (f && !f.error) {
        if (f.job_titles?.length) setJobTitle(f.job_titles[0])
        if (f.locations?.length) setLocation(f.locations[0])
        if (f.platform) setPlatform(f.platform)
        if (f.max_applications) setMaxApps(f.max_applications)
        if (f.selected_cv_id) setSelectedCv(f.selected_cv_id)
      }
    })
  }, [])

  const launch = async () => {
    if (!jobTitle.trim()) return
    setLaunching(true)
    // Save filters then start bot
    await api.updateFilters({
      job_titles: [jobTitle.trim()],
      locations: location.trim() ? [location.trim()] : ['deutschland'],
      platform,
      max_applications: maxApps,
      selected_cv_id: selectedCv,
    })
    await api.startBot('scrape_and_apply')
    navigate('/bot')
  }

  if (!stats)
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-pulse text-[11px] font-bold uppercase tracking-[0.2em] text-white/20">
          Initializing Mission Control...
        </div>
      </div>
    )

  const statCards = [
    {
      label: 'Live Applications',
      val: stats.total_applications.toLocaleString(),
      accent: 'text-amber-500',
    },
    { label: 'Success Rate', val: `${stats.success_rate}%`, accent: 'text-[#27C93F]' },
    {
      label: 'Jobs Discovered',
      val: stats.total_jobs_discovered.toLocaleString(),
      accent: 'text-white',
    },
    {
      label: 'Responses',
      val: Object.entries(stats.by_response || {})
        .filter(([k]) => k !== 'waiting' && k !== 'PENDING')
        .reduce((s: number, [, v]) => s + (v as number), 0)
        .toString(),
      accent: 'text-blue-400',
    },
  ]

  const platformData = Object.entries(stats.by_platform || {}) as [string, number][]
  const statusData = Object.entries(stats.by_status || {}) as [string, number][]

  return (
    <div className="space-y-8 p-8">
      {/* Header */}
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
                d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                strokeLinecap="round"
                strokeWidth="2.5"
              />
            </svg>
          </div>
          <span className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">
            Mission Control
          </span>
        </div>
        <div className="flex items-center gap-2 rounded-md border border-[#27C93F]/20 bg-[#27C93F]/5 px-3 py-1.5">
          <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#27C93F]"></div>
          <span className="text-[8px] font-bold uppercase tracking-widest text-[#27C93F]">
            Active
          </span>
        </div>
      </div>

      {/* Quick Launch */}
      <div className="rounded-2xl border border-amber-500/20 bg-[#0A0A0A] p-8">
        <div className="mb-6 flex items-center gap-2">
          <svg
            className="h-5 w-5 text-amber-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path d="M13 10V3L4 14h7v7l9-11h-7z" strokeLinecap="round" strokeWidth="2.5" />
          </svg>
          <span className="text-[9px] font-black uppercase tracking-[0.25em] text-amber-500">
            Quick Launch — Start Applying
          </span>
        </div>
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="mb-2 block text-[8px] font-black uppercase tracking-[0.2em] text-white/20">
              What position?
            </label>
            <input
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && launch()}
              placeholder="e.g. Kellner, Project Manager, Barista..."
              className="w-full rounded-xl border border-white/10 bg-black px-5 py-4 text-lg text-white transition-colors placeholder:text-white/15 focus:border-amber-500/50 focus:outline-none"
            />
          </div>
          <div className="w-56">
            <label className="mb-2 block text-[8px] font-black uppercase tracking-[0.2em] text-white/20">
              Where?
            </label>
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && launch()}
              placeholder="e.g. Berlin, München..."
              className="w-full rounded-xl border border-white/10 bg-black px-5 py-4 text-lg text-white transition-colors placeholder:text-white/15 focus:border-amber-500/50 focus:outline-none"
            />
          </div>
          <div className="w-56">
            <label className="mb-2 block text-[8px] font-black uppercase tracking-[0.2em] text-white/20">
              Platform
            </label>
            <div className="flex gap-1.5">
              {(['stepstone', 'xing', 'indeed', 'linkedin'] as const).map((p) => (
                <button
                  key={p}
                  onClick={() => setPlatform(p)}
                  className={`flex-1 rounded-xl border py-4 text-[9px] font-black uppercase tracking-wider transition-all ${
                    platform === p
                      ? 'border-amber-500/30 bg-amber-500/10 text-amber-500'
                      : 'border-white/5 bg-black text-white/25 hover:border-white/10 hover:text-white/50'
                  }`}
                >
                  {p === 'stepstone' ? 'SS' : p === 'indeed' ? 'IN' : p === 'xing' ? 'XI' : 'LI'}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-end">
            <button
              onClick={launch}
              disabled={launching || !jobTitle.trim()}
              className="whitespace-nowrap rounded-xl bg-amber-500 px-8 py-4 text-sm font-black uppercase tracking-wider text-white shadow-lg shadow-amber-500/25 transition-all hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-30"
            >
              {launching ? 'Launching...' : 'Go →'}
            </button>
          </div>
        </div>
        {/* Applications slider + CV picker — own row */}
        <div className="mt-4 flex items-center gap-6 border-t border-white/5 pt-4">
          <div className="flex items-center gap-3">
            <span className="whitespace-nowrap text-[8px] font-black uppercase tracking-[0.2em] text-white/20">
              Applications
            </span>
            <input
              type="range"
              min={1}
              max={500}
              value={maxApps}
              onChange={(e) => setMaxApps(Number(e.target.value))}
              className="h-1.5 w-40 accent-amber-500"
            />
            <span className="w-8 text-center text-xl font-black tabular-nums text-amber-500">
              {maxApps}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="whitespace-nowrap text-[8px] font-black uppercase tracking-[0.2em] text-white/20">
              CV
            </span>
            <select
              value={selectedCv || ''}
              onChange={(e) => setSelectedCv(e.target.value ? Number(e.target.value) : null)}
              className="cursor-pointer appearance-none rounded-lg border border-white/10 bg-black px-3 py-1.5 text-sm text-white focus:border-amber-500/30 focus:outline-none"
            >
              <option value="">No CV (use platform default)</option>
              {cvs.map((cv: any) => (
                <option key={cv.id} value={cv.id}>
                  {cv.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <p className="mt-3 text-[10px] text-white/15">
          Type a job title, pick a city, hit Go — the bot scrapes jobs and auto-applies for you.
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-6">
        {statCards.map((stat, i) => (
          <div
            key={i}
            className="space-y-2 rounded-xl border border-white/5 bg-[#0A0A0A] p-5 transition-colors hover:border-white/10"
          >
            <span className="text-[8px] font-black uppercase tracking-[0.2em] text-white/20">
              {stat.label}
            </span>
            <p className={`text-3xl font-black tracking-tighter ${stat.accent}`}>{stat.val}</p>
          </div>
        ))}
      </div>

      {/* Platform + Status breakdown */}
      <div className="grid grid-cols-2 gap-6">
        {/* By Platform */}
        <div className="rounded-xl border border-white/5 bg-[#0A0A0A] p-6">
          <span className="mb-4 block text-[8px] font-black uppercase tracking-[0.2em] text-white/20">
            By Platform
          </span>
          <div className="space-y-3">
            {platformData.map(([name, count]) => {
              const max = Math.max(...platformData.map(([, v]) => v))
              const pct = (count / max) * 100
              const colors: Record<string, string> = {
                stepstone: 'bg-amber-500',
                xing: 'bg-emerald-500',
                indeed: 'bg-purple-500',
                linkedin: 'bg-blue-500',
                testplatform: 'bg-white/20',
              }
              return (
                <div key={name} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-white/40">
                      {name}
                    </span>
                    <span className="text-[10px] font-black text-white/60">
                      {count.toLocaleString()}
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
                    <div
                      className={`h-full rounded-full ${colors[name] || 'bg-white/20'}`}
                      style={{ width: `${pct}%` }}
                    ></div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* By Status */}
        <div className="rounded-xl border border-white/5 bg-[#0A0A0A] p-6">
          <span className="mb-4 block text-[8px] font-black uppercase tracking-[0.2em] text-white/20">
            By Status
          </span>
          <div className="space-y-3">
            {statusData.map(([name, count]) => {
              const max = Math.max(...statusData.map(([, v]) => v))
              const pct = (count / max) * 100
              const colors: Record<string, string> = {
                success: 'bg-[#27C93F]',
                failed: 'bg-red-500',
                pending: 'bg-amber-500',
                skipped: 'bg-white/20',
              }
              return (
                <div key={name} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-white/40">
                      {name}
                    </span>
                    <span className="text-[10px] font-black text-white/60">
                      {count.toLocaleString()}
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
                    <div
                      className={`h-full rounded-full ${colors[name] || 'bg-white/20'}`}
                      style={{ width: `${pct}%` }}
                    ></div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Recent Applications - Audit Log Style */}
      <div className="rounded-xl border border-white/5 bg-[#0A0A0A] p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-black text-amber-500">_</span>
            <span className="text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
              Recent Activity
            </span>
          </div>
          <div className="flex items-center gap-1.5 rounded bg-amber-500/10 px-2 py-0.5">
            <div className="h-1 w-1 animate-pulse rounded-full bg-amber-500"></div>
            <span className="text-[7px] font-black uppercase text-amber-500">Live</span>
          </div>
        </div>
        <div className="space-y-2 font-mono text-[12px]">
          {(stats.recent || []).map((a: any) => {
            const statusColors: Record<string, string> = {
              success: 'text-[#27C93F]',
              failed: 'text-red-400',
              pending: 'text-amber-500',
              applying: 'text-blue-400',
            }
            return (
              <div
                key={a.id}
                className="group flex gap-6 rounded-lg px-2 py-1.5 transition-colors hover:bg-white/[0.02]"
              >
                <span className="w-20 shrink-0 tabular-nums text-white/15">
                  {a.applied_at?.split('T')[1]?.slice(0, 8) || '--:--:--'}
                </span>
                <span
                  className={`mt-0.5 h-fit min-w-[60px] shrink-0 rounded border px-1.5 py-0.5 text-center text-[9px] font-black uppercase tracking-wider ${
                    a.status === 'success'
                      ? 'border-[#27C93F]/20 bg-[#27C93F]/10 text-[#27C93F]'
                      : a.status === 'failed'
                        ? 'border-red-500/20 bg-red-500/10 text-red-400'
                        : a.status === 'external'
                          ? 'border-purple-500/20 bg-purple-500/10 text-purple-400'
                          : 'border-amber-500/20 bg-amber-500/10 text-amber-500'
                  }`}
                >
                  {a.status}
                </span>
                <span className="truncate tracking-tight text-white/50 transition-colors group-hover:text-white/80">
                  {a.job_title || 'Unknown Position'}
                </span>
                <span className="ml-auto shrink-0 text-white/20">{a.company || ''}</span>
                <span className="shrink-0 text-[9px] font-bold uppercase text-white/10">
                  {a.platform}
                </span>
              </div>
            )
          })}
          <div className="mt-2 animate-pulse px-2 text-lg font-bold tracking-widest text-white/20">
            _
          </div>
        </div>
      </div>
    </div>
  )
}
