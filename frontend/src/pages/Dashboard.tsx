import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Rocket,
  Activity,
  CheckCircle2,
  MessageSquare,
  Briefcase,
  MapPin,
  Globe,
  SlidersHorizontal,
  FileText,
  ArrowRight,
} from 'lucide-react'
import { api } from '../api'

export default function Dashboard({ isGuest = false }: { isGuest?: boolean }) {
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
    if (isGuest) {
      // Show demo data for guests
      setStats({
        total_applications: 0,
        success_rate: 0,
        by_response: {},
        by_platform: { stepstone: 0, linkedin: 0 },
        by_status: {},
        recent: [],
      })
      return
    }
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
  }, [isGuest])

  const launch = async () => {
    if (!jobTitle.trim()) return
    setLaunching(true)
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

  const statCards = [
    {
      label: 'Live Applications',
      val: stats?.total_applications?.toLocaleString() || '0',
      accent: 'text-amber-500',
      icon: Activity,
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20'
    },
    {
      label: 'Success Rate',
      val: `${stats?.success_rate || 0}%`,
      accent: 'text-emerald-400',
      icon: CheckCircle2,
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20'
    },
{
      label: 'Responses',
      val: stats ? Object.entries(stats.by_response || {})
        .filter(([k]) => k !== 'waiting' && k !== 'PENDING')
        .reduce((s: number, [, v]) => s + (v as number), 0)
        .toString() : '0',
      accent: 'text-purple-400',
      icon: MessageSquare,
      bg: 'bg-purple-500/10',
      border: 'border-purple-500/20'
    },
  ]

  const platformData = stats ? Object.entries(stats.by_platform || {}) as [string, number][] : []
  const statusData = stats ? Object.entries(stats.by_status || {}) as [string, number][] : []

  return (
    <div className="space-y-6 sm:space-y-8 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="shrink-0 rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
            <Activity className="h-5 w-5 text-amber-500" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white truncate">Mission Control</h1>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
              System Overview
            </p>
          </div>
        </div>
        <div className="shrink-0 flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-2 sm:px-3 py-1.5 backdrop-blur-sm">
          <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
          <span className="hidden sm:inline text-[9px] font-bold uppercase tracking-widest text-emerald-500">
            System Active
          </span>
        </div>
      </div>

      {/* Quick Launch */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#0A0A0A] p-4 sm:p-6 md:p-8 shadow-2xl transition-all hover:border-white/20">
        <div className="absolute top-0 right-0 p-32 bg-amber-500/5 blur-[100px] rounded-full pointer-events-none"></div>

        <div className="relative z-10">
          <div className="mb-8 flex items-center gap-3">
            <div className="rounded-lg bg-amber-500/20 p-1.5">
              <Rocket className="h-5 w-5 text-amber-500" />
            </div>
            <span className="text-xs font-black uppercase tracking-[0.2em] text-amber-500">
              Quick Launch
            </span>
          </div>

          <div className="grid gap-6 md:grid-cols-12">
            <div className="md:col-span-5">
              <label className="mb-2 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                <Briefcase className="h-3 w-3" /> Target Position
              </label>
              <input
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && launch()}
                placeholder="e.g. Frontend Engineer, Product Manager..."
                className="w-full rounded-xl border border-white/10 bg-black/50 px-5 py-4 text-base text-white transition-all placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
              />
            </div>

            <div className="md:col-span-3">
              <label className="mb-2 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                <MapPin className="h-3 w-3" /> Location
              </label>
              <input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && launch()}
                placeholder="e.g. Berlin, Remote..."
                className="w-full rounded-xl border border-white/10 bg-black/50 px-5 py-4 text-base text-white transition-all placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
              />
            </div>

            <div className="md:col-span-4">
              <label className="mb-2 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                <Globe className="h-3 w-3" /> Platform
              </label>
              <div className="flex h-[58px] gap-1.5 rounded-xl border border-white/10 bg-black/50 p-1.5">
                {(['stepstone', 'xing', 'indeed', 'linkedin'] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPlatform(p)}
                    className={`flex-1 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all ${
                      platform === p
                        ? 'bg-amber-500 text-black shadow-md scale-100'
                        : 'text-white/40 hover:bg-white/5 hover:text-white/80 scale-95 hover:scale-100'
                    }`}
                  >
                    {p === 'stepstone' ? 'SS' : p === 'indeed' ? 'IN' : p === 'xing' ? 'XI' : 'LI'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-6 flex flex-col sm:flex-row sm:flex-wrap sm:items-end sm:justify-between gap-4 sm:gap-6 border-t border-white/5 pt-6">
            <div className="flex flex-col sm:flex-row sm:flex-wrap items-start sm:items-center gap-4 sm:gap-8">
              <div className="flex items-center gap-4 w-full sm:w-auto">
                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                  <SlidersHorizontal className="h-3 w-3" /> Volume
                </div>
                <input
                  type="range"
                  min={1}
                  max={500}
                  value={maxApps}
                  onChange={(e) => setMaxApps(Number(e.target.value))}
                  className="h-1.5 flex-1 sm:w-32 sm:flex-none cursor-pointer appearance-none rounded-full bg-white/10 accent-amber-500"
                />
                <span className="w-12 text-right text-lg font-black tabular-nums text-amber-500">
                  {maxApps}
                </span>
              </div>

              <div className="flex items-center gap-4 w-full sm:w-auto">
                <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-white/40 shrink-0">
                  <FileText className="h-3 w-3" /> Resume
                </div>
                <select
                  value={selectedCv || ''}
                  onChange={(e) => setSelectedCv(e.target.value ? Number(e.target.value) : null)}
                  className="flex-1 sm:flex-none cursor-pointer appearance-none rounded-lg border border-white/10 bg-black/50 px-4 py-2 text-sm text-white transition-colors focus:border-amber-500/50 focus:outline-none"
                >
                  <option value="">Default Platform CV</option>
                  {cvs.map((cv: any) => (
                    <option key={cv.id} value={cv.id}>
                      {cv.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {isGuest ? (
              <Link
                to="/login?register=1"
                className="group relative w-full sm:w-auto overflow-hidden rounded-xl bg-amber-500 px-8 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_20px_rgba(245,158,11,0.3)] transition-all hover:scale-[1.02] hover:bg-amber-400 hover:shadow-[0_0_30px_rgba(245,158,11,0.5)] active:scale-[0.98] text-center block"
              >
                <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
                <span className="relative flex items-center justify-center gap-2">
                  Subscribe — €8/mo
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </span>
              </Link>
            ) : (
              <button
                onClick={launch}
                disabled={launching || !jobTitle.trim()}
                className="group relative w-full sm:w-auto overflow-hidden rounded-xl bg-amber-500 px-8 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_20px_rgba(245,158,11,0.3)] transition-all hover:scale-[1.02] hover:bg-amber-400 hover:shadow-[0_0_30px_rgba(245,158,11,0.5)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
              >
                <div className="absolute inset-0 flex h-full w-full justify-center [transform:skew(-12deg)_translateX(-100%)] group-hover:duration-1000 group-hover:[transform:skew(-12deg)_translateX(100%)]">
                  <div className="relative h-full w-8 bg-white/20" />
                </div>
                <span className="relative flex items-center justify-center gap-2">
                  {launching ? 'Initializing...' : 'Launch Sequence'}
                  {!launching && <Rocket className="h-4 w-4" />}
                </span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat, i) => (
          <div
            key={i}
            className="stat-card group relative overflow-hidden rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 transition-all hover:border-white/10 hover:bg-white/[0.02] hover:-translate-y-1"
          >
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                {stat.label}
              </span>
              <div className={`stat-icon-bg rounded-lg p-2 ${stat.bg} ${stat.border} border`}>
                <stat.icon className={`h-4 w-4 ${stat.accent}`} />
              </div>
            </div>
            {!stats ? (
              <div className="h-10 w-24 rounded-lg shimmer"></div>
            ) : (
              <p className={`text-4xl font-black tracking-tighter ${stat.accent}`}>{stat.val}</p>
            )}
          </div>
        ))}
      </div>

      {/* Breakdown & Activity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-1">
          <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 transition-all hover:border-white/10">
            <span className="mb-6 block text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
              Platform Distribution
            </span>
            <div className="space-y-5">
              {!stats ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="space-y-2">
                    <div className="flex justify-between">
                      <div className="h-3 w-16 rounded shimmer"></div>
                      <div className="h-3 w-8 rounded shimmer"></div>
                    </div>
                    <div className="h-2 w-full rounded-full shimmer"></div>
                  </div>
                ))
              ) : platformData.length > 0 ? platformData.map(([name, count]) => {
                const max = Math.max(...platformData.map(([, v]) => v))
                const pct = (count / max) * 100
                const colors: Record<string, string> = {
                  stepstone: 'bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.5)]',
                  xing: 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]',
                  indeed: 'bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]',
                  linkedin: 'bg-blue-400 shadow-[0_0_10px_rgba(96,165,250,0.5)]',
                }
                return (
                  <div key={name} className="space-y-2 group">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-white/60 group-hover:text-white transition-colors">
                        {name}
                      </span>
                      <span className="text-[11px] font-black tabular-nums text-white">
                        {count.toLocaleString()}
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                      <div
                        className={`h-full rounded-full transition-all duration-1000 ease-out ${colors[name] || 'bg-white/20'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              }) : (
                <div className="py-4 text-center text-[10px] text-white/20 uppercase tracking-wider font-bold">No data available</div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 transition-all hover:border-white/10">
            <span className="mb-6 block text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
              Status Breakdown
            </span>
            <div className="space-y-5">
              {!stats ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="space-y-2">
                    <div className="flex justify-between">
                      <div className="h-3 w-16 rounded shimmer"></div>
                      <div className="h-3 w-8 rounded shimmer"></div>
                    </div>
                    <div className="h-2 w-full rounded-full shimmer"></div>
                  </div>
                ))
              ) : statusData.length > 0 ? statusData.map(([name, count]) => {
                const max = Math.max(...statusData.map(([, v]) => v))
                const pct = (count / max) * 100
                const colors: Record<string, string> = {
                  success: 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]',
                  failed: 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]',
                  pending: 'bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.5)]',
                  skipped: 'bg-white/20',
                }
                return (
                  <div key={name} className="space-y-2 group">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-white/60 group-hover:text-white transition-colors">
                        {name}
                      </span>
                      <span className="text-[11px] font-black tabular-nums text-white">
                        {count.toLocaleString()}
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
                      <div
                        className={`h-full rounded-full transition-all duration-1000 ease-out ${colors[name] || 'bg-white/20'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              }) : (
                <div className="py-4 text-center text-[10px] text-white/20 uppercase tracking-wider font-bold">No data available</div>
              )}
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 lg:col-span-2 flex flex-col transition-all hover:border-white/10">
          <div className="mb-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Activity className="h-4 w-4 text-amber-500" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                Audit Log
              </span>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-amber-500/10 px-3 py-1.5 border border-amber-500/20">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500"></div>
              <span className="text-[9px] font-black uppercase tracking-widest text-amber-500">Live Feed</span>
            </div>
          </div>

          <div className="flex-1 space-y-2 font-mono text-xs overflow-y-auto pr-2 custom-scrollbar">
            {!stats ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6 rounded-xl border border-white/5 bg-black/50 p-3">
                  <div className="h-4 w-16 rounded shimmer"></div>
                  <div className="h-4 w-12 rounded shimmer"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-3/4 rounded shimmer"></div>
                    <div className="h-3 w-1/2 rounded shimmer"></div>
                  </div>
                </div>
              ))
            ) : (stats.recent || []).length > 0 ? (stats.recent || []).map((a: any) => (
              <div
                key={a.id}
                className="group flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6 rounded-xl border border-white/5 bg-black/50 p-3 transition-all hover:-translate-y-0.5 hover:border-white/10 hover:bg-white/[0.02] hover:shadow-lg"
              >
                <div className="flex items-center gap-4 sm:w-32 shrink-0">
                  <span className="tabular-nums text-white/30 text-[10px]">
                    {a.applied_at?.split('T')[1]?.slice(0, 8) || '--:--:--'}
                  </span>
                  <span
                    className={`rounded-md border px-2 py-1 text-center text-[9px] font-black uppercase tracking-wider ${
                      a.status === 'success'
                        ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
                        : a.status === 'failed'
                          ? 'border-red-500/20 bg-red-500/10 text-red-400'
                          : a.status === 'external'
                            ? 'border-purple-500/20 bg-purple-500/10 text-purple-400'
                            : 'border-amber-500/20 bg-amber-500/10 text-amber-500'
                    }`}
                  >
                    {a.status}
                  </span>
                </div>
                <div className="flex-1 min-w-0 flex flex-col">
                  <span className="truncate font-sans font-bold text-white/80 transition-colors group-hover:text-white">
                    {a.job_title || 'Unknown Position'}
                  </span>
                  <span className="truncate font-sans text-[10px] text-white/40">
                    {a.company || 'Unknown Company'}
                  </span>
                </div>
                <div className="shrink-0 self-start sm:self-center">
                  <span className="rounded-lg bg-white/5 px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider text-white/30">
                    {a.platform}
                  </span>
                </div>
              </div>
            )) : (
              <div className="flex h-full items-center justify-center text-[10px] text-white/20 uppercase tracking-wider font-bold">
                No recent activity
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
