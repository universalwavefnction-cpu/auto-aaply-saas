import { useState, useEffect, useCallback } from 'react'
import {
  Radar,
  Search,
  MapPin,
  Building2,
  ExternalLink,
  Zap,
  CheckCircle2,
  Clock,
  Briefcase,
  Globe,
  X,
  Filter,
  ArrowUpDown,
  DollarSign,
  Calendar,
  ChevronDown,
  RotateCcw,
} from 'lucide-react'
import { api } from '../api'

const PLATFORM_META: Record<string, { label: string; color: string }> = {
  arbeitsagentur: { label: 'Arbeitsagentur', color: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  linkedin_guest: { label: 'LinkedIn', color: 'bg-sky-500/10 text-sky-400 border-sky-500/20' },
  arbeitnow: { label: 'Arbeitnow', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  stepstone: { label: 'StepStone', color: 'bg-amber-500/10 text-amber-500 border-amber-500/20' },
  xing: { label: 'Xing', color: 'bg-teal-500/10 text-teal-400 border-teal-500/20' },
  indeed: { label: 'Indeed', color: 'bg-purple-500/10 text-purple-400 border-purple-500/20' },
  jooble: { label: 'Jooble', color: 'bg-orange-500/10 text-orange-400 border-orange-500/20' },
  adzuna: { label: 'Adzuna', color: 'bg-pink-500/10 text-pink-400 border-pink-500/20' },
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return 'Today'
  if (days === 1) return '1 day ago'
  if (days < 30) return `${days} days ago`
  return `${Math.floor(days / 30)}mo ago`
}

export default function Discovery() {
  const [jobs, setJobs] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [location, setLocation] = useState('')
  const [platform, setPlatform] = useState('')
  const [employmentType, setEmploymentType] = useState('')
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [sortBy, setSortBy] = useState('')
  const [salaryMin, setSalaryMin] = useState('')
  const [salaryMax, setSalaryMax] = useState('')
  const [postedDays, setPostedDays] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [facets, setFacets] = useState<{ locations: string[]; platforms: string[]; employment_types: string[] }>({ locations: [], platforms: [], employment_types: [] })
  const [loading, setLoading] = useState(true)
  const [discovering, setDiscovering] = useState(false)
  const [discoverQuery, setDiscoverQuery] = useState('')
  const [discoverLocation, setDiscoverLocation] = useState('')
  const [lastQuery, setLastQuery] = useState('')
  const [selectedJob, setSelectedJob] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [applying, setApplying] = useState<number | null>(null)
  const [toast, setToast] = useState<{ show: boolean; msg: string }>({ show: false, msg: '' })

  const showToast = (msg: string) => {
    setToast({ show: true, msg })
    setTimeout(() => setToast({ show: false, msg: '' }), 3000)
  }

  const fetchJobs = useCallback(async () => {
    setLoading(true)
    const params: Record<string, any> = { page: String(page), per_page: '20' }
    if (search) params.search = search
    if (location) params.location = location
    if (platform) params.platform = platform
    if (employmentType) params.employment_type = employmentType
    if (remoteOnly) params.remote = 'true'
    if (sortBy) params.sort_by = sortBy
    if (salaryMin) params.salary_min = salaryMin
    if (salaryMax) params.salary_max = salaryMax
    if (postedDays) params.posted_days = postedDays
    const res = await api.getJobs(params)
    setJobs(res.jobs || [])
    setTotal(res.total || 0)
    setLoading(false)
  }, [page, search, location, platform, employmentType, remoteOnly, sortBy, salaryMin, salaryMax, postedDays])

  useEffect(() => {
    fetchJobs()
  }, [fetchJobs])

  useEffect(() => {
    api.getJobFacets().then((f: any) => { if (f && !f.error) setFacets(f) })
  }, [])

  const handleDiscover = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    setDiscovering(true)
    const opts: { query?: string; location?: string } = {}
    if (discoverQuery.trim()) opts.query = discoverQuery.trim()
    if (discoverLocation.trim()) opts.location = discoverLocation.trim()
    try {
      const res = await api.discoverJobs(Object.keys(opts).length ? opts : undefined)
      if (res.error || res.detail) {
        showToast(res.detail || res.error || 'Discovery failed')
        setDiscovering(false)
        return
      }
      setLastQuery(discoverQuery.trim())
      showToast(
        opts.query
          ? `Scanning all platforms for "${opts.query}"...`
          : 'Scanning platforms with saved job titles...'
      )
      const poll = setInterval(async () => {
        const status = await api.discoveryStatus()
        if (!status.running) {
          clearInterval(poll)
          setDiscovering(false)
          setPage(1)
          // If user searched a specific query, filter results to show it
          if (opts.query) setSearch(opts.query)
          fetchJobs()
          showToast('Discovery complete!')
        }
      }, 3000)
    } catch {
      setDiscovering(false)
      showToast('Failed to start discovery')
    }
  }

  const openDetail = async (job: any) => {
    setDetailLoading(true)
    setSelectedJob(job)
    try {
      const full = await api.getJob(job.id)
      if (full && !full.error) {
        setSelectedJob(full)
      }
    } catch {
      // keep partial data
    }
    setDetailLoading(false)
  }

  const handleApply = async (job: any) => {
    setApplying(job.id)
    await api.manualApply({
      job_id: job.id,
      platform: job.platform,
      job_title: job.title,
      company: job.company,
      url: job.url,
    })
    window.open(job.url, '_blank')
    setApplying(null)
    showToast('Application logged — opening job page')
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    fetchJobs()
  }

  return (
    <div className="space-y-6 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto relative">
      {/* Toast */}
      <div
        className={`fixed top-[60px] md:top-8 right-4 sm:right-8 left-4 sm:left-auto z-50 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm font-bold text-emerald-400 shadow-2xl backdrop-blur-md transition-all duration-300 ${toast.show ? 'translate-y-0 opacity-100' : '-translate-y-4 opacity-0 pointer-events-none'}`}
      >
        <CheckCircle2 className="h-4 w-4" />
        {toast.msg}
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
            <Radar className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Job Discovery</h1>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
              Multi-Platform Scanner
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-[#0A0A0A] px-4 py-2 shadow-lg">
          <span className="text-[10px] font-black uppercase tracking-wider text-white/40">
            Total Jobs
          </span>
          <span className="text-sm font-bold text-amber-500">{total}</span>
        </div>
      </div>

      {/* Discovery Search — the main action */}
      <form
        onSubmit={handleDiscover}
        className="rounded-2xl border border-amber-500/20 bg-gradient-to-b from-amber-500/5 to-transparent p-5 shadow-2xl"
      >
        <div className="mb-3 flex items-center gap-2">
          <Radar className="h-4 w-4 text-amber-500" />
          <span className="text-[10px] font-black uppercase tracking-[0.15em] text-amber-500">
            Search All Job Boards
          </span>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1 group">
            <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-white/20 transition-colors group-focus-within:text-amber-500" />
            <input
              type="text"
              value={discoverQuery}
              onChange={(e) => setDiscoverQuery(e.target.value)}
              placeholder="e.g. Data Engineer, Marketing Manager, Product Designer..."
              className="w-full rounded-xl border border-white/10 bg-black/50 pl-12 pr-4 py-4 text-sm text-white transition-all placeholder:text-white/25 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            />
          </div>
          <div className="relative sm:w-52 group">
            <MapPin className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-white/20 transition-colors group-focus-within:text-amber-500" />
            <input
              type="text"
              value={discoverLocation}
              onChange={(e) => setDiscoverLocation(e.target.value)}
              placeholder="Location (optional)"
              className="w-full rounded-xl border border-white/10 bg-black/50 pl-12 pr-4 py-4 text-sm text-white transition-all placeholder:text-white/25 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            />
          </div>
          <button
            type="submit"
            disabled={discovering}
            className="group relative flex items-center justify-center gap-2 overflow-hidden rounded-xl bg-amber-500 px-8 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_20px_rgba(245,158,11,0.2)] transition-all hover:bg-amber-400 active:scale-95 disabled:opacity-70 shrink-0"
          >
            {discovering ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-black border-t-transparent" />
                <span>Scanning...</span>
              </>
            ) : (
              <>
                <div className="absolute inset-0 flex h-full w-full justify-center [transform:skew(-12deg)_translateX(-100%)] group-hover:duration-1000 group-hover:[transform:skew(-12deg)_translateX(100%)]">
                  <div className="relative h-full w-8 bg-white/20" />
                </div>
                <Radar className="relative h-4 w-4" />
                <span className="relative">Discover</span>
              </>
            )}
          </button>
        </div>
        <p className="mt-2 text-[10px] text-white/20">
          {discoverQuery.trim()
            ? `Will search "${discoverQuery.trim()}" across Arbeitsagentur, LinkedIn, Arbeitnow, Indeed, Jooble, Adzuna`
            : 'Type a specific job title to search all platforms, or leave empty to use your saved job titles from Settings'}
        </p>
      </form>

      {lastQuery && (
        <div className="flex items-center gap-2 text-xs text-white/40">
          <Search className="h-3 w-3" />
          <span>
            Last discovery: "<span className="text-amber-500 font-bold">{lastQuery}</span>"
          </span>
        </div>
      )}

      {/* Filters Panel */}
      <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] shadow-2xl overflow-hidden">
        {/* Quick filter bar — always visible */}
        <div className="flex flex-wrap items-center gap-2 p-4">
          <div className="relative flex-1 min-w-[200px] group">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/20 group-focus-within:text-amber-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              onKeyDown={(e) => e.key === 'Enter' && fetchJobs()}
              placeholder="Filter results by title or company..."
              className="w-full rounded-lg border border-white/5 bg-black/50 pl-9 pr-3 py-2 text-xs text-white placeholder:text-white/20 focus:border-amber-500/50 focus:outline-none"
            />
          </div>

          {/* Platform */}
          <select value={platform} onChange={(e) => { setPlatform(e.target.value); setPage(1) }} className="appearance-none rounded-lg border border-white/10 bg-black/50 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-white/60 focus:border-amber-500/50 focus:outline-none">
            <option value="">All Platforms</option>
            {(facets.platforms.length ? facets.platforms : ['arbeitsagentur','linkedin_guest','arbeitnow','stepstone','xing','indeed']).map(p => (
              <option key={p} value={p}>{PLATFORM_META[p]?.label || p}</option>
            ))}
          </select>

          {/* Remote */}
          <button type="button" onClick={() => { setRemoteOnly(!remoteOnly); setPage(1) }}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-[10px] font-bold uppercase tracking-wider transition-colors ${remoteOnly ? 'border-amber-500/30 bg-amber-500/10 text-amber-500' : 'border-white/10 bg-black/50 text-white/40 hover:text-white/60'}`}
          >
            <Globe className="h-3 w-3" />Remote
          </button>

          {/* Expand filters */}
          <button type="button" onClick={() => setFiltersOpen(!filtersOpen)}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-[10px] font-bold uppercase tracking-wider transition-colors ${filtersOpen ? 'border-amber-500/30 bg-amber-500/10 text-amber-500' : 'border-white/10 bg-black/50 text-white/40 hover:text-white/60'}`}
          >
            <Filter className="h-3 w-3" />Filters
            <ChevronDown className={`h-3 w-3 transition-transform ${filtersOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* Active filter count */}
          {(location || employmentType || salaryMin || salaryMax || postedDays || remoteOnly) && (
            <button type="button" onClick={() => { setLocation(''); setEmploymentType(''); setSalaryMin(''); setSalaryMax(''); setPostedDays(''); setRemoteOnly(false); setPage(1) }}
              className="flex items-center gap-1 rounded-lg border border-red-500/20 bg-red-500/5 px-2 py-2 text-[10px] font-bold text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <RotateCcw className="h-3 w-3" />Clear
            </button>
          )}

          {/* Sort */}
          <div className="ml-auto flex items-center gap-1.5">
            <ArrowUpDown className="h-3 w-3 text-white/20" />
            <select value={sortBy} onChange={(e) => { setSortBy(e.target.value); setPage(1) }}
              className="appearance-none rounded-lg border border-white/10 bg-black/50 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-white/60 focus:border-amber-500/50 focus:outline-none"
            >
              <option value="">Newest Scraped</option>
              <option value="posted_at">Posted Date</option>
              <option value="company">Company A-Z</option>
              <option value="salary">Highest Salary</option>
            </select>
          </div>
        </div>

        {/* Expanded filters — collapsible */}
        <div className={`transition-all duration-300 overflow-hidden ${filtersOpen ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}>
          <div className="border-t border-white/5 p-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* City / Location */}
            <div>
              <label className="block mb-2 text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
                <MapPin className="inline h-3 w-3 mr-1" />City / Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => { setLocation(e.target.value); setPage(1) }}
                placeholder="e.g. Berlin, Munich, Hamburg..."
                className="w-full rounded-lg border border-white/10 bg-black/50 px-3 py-2.5 text-xs text-white placeholder:text-white/20 focus:border-amber-500/50 focus:outline-none"
                list="location-suggestions"
              />
              <datalist id="location-suggestions">
                {facets.locations.slice(0, 20).map(l => <option key={l} value={l} />)}
              </datalist>
            </div>

            {/* Employment Type */}
            <div>
              <label className="block mb-2 text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
                <Briefcase className="inline h-3 w-3 mr-1" />Employment Type
              </label>
              <select value={employmentType} onChange={(e) => { setEmploymentType(e.target.value); setPage(1) }}
                className="w-full appearance-none rounded-lg border border-white/10 bg-black/50 px-3 py-2.5 text-xs text-white/60 focus:border-amber-500/50 focus:outline-none"
              >
                <option value="">Any type</option>
                <option value="full-time">Full-time</option>
                <option value="part-time">Part-time</option>
                <option value="contract">Contract</option>
                <option value="mini-job">Mini-Job</option>
                {facets.employment_types.filter(t => !['full-time','part-time','contract','mini-job'].includes(t)).map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            {/* Salary Range */}
            <div>
              <label className="block mb-2 text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
                <DollarSign className="inline h-3 w-3 mr-1" />Salary Range (EUR/year)
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={salaryMin}
                  onChange={(e) => { setSalaryMin(e.target.value); setPage(1) }}
                  placeholder="Min"
                  className="w-1/2 rounded-lg border border-white/10 bg-black/50 px-3 py-2.5 text-xs text-white placeholder:text-white/20 focus:border-amber-500/50 focus:outline-none"
                />
                <input
                  type="number"
                  value={salaryMax}
                  onChange={(e) => { setSalaryMax(e.target.value); setPage(1) }}
                  placeholder="Max"
                  className="w-1/2 rounded-lg border border-white/10 bg-black/50 px-3 py-2.5 text-xs text-white placeholder:text-white/20 focus:border-amber-500/50 focus:outline-none"
                />
              </div>
            </div>

            {/* Posted Date */}
            <div>
              <label className="block mb-2 text-[9px] font-black uppercase tracking-[0.2em] text-white/40">
                <Calendar className="inline h-3 w-3 mr-1" />Posted Within
              </label>
              <select value={postedDays} onChange={(e) => { setPostedDays(e.target.value); setPage(1) }}
                className="w-full appearance-none rounded-lg border border-white/10 bg-black/50 px-3 py-2.5 text-xs text-white/60 focus:border-amber-500/50 focus:outline-none"
              >
                <option value="">Any time</option>
                <option value="1">Last 24 hours</option>
                <option value="3">Last 3 days</option>
                <option value="7">Last week</option>
                <option value="14">Last 2 weeks</option>
                <option value="30">Last month</option>
              </select>
            </div>
          </div>

          {/* Quick city chips from facets */}
          {facets.locations.length > 0 && (
            <div className="border-t border-white/5 px-4 py-3">
              <span className="text-[9px] font-black uppercase tracking-[0.15em] text-white/30 mr-2">Popular cities:</span>
              <div className="inline-flex flex-wrap gap-1.5 mt-1">
                {facets.locations.slice(0, 12).map(city => (
                  <button key={city} type="button"
                    onClick={() => { setLocation(city === location ? '' : city); setPage(1) }}
                    className={`rounded border px-2 py-0.5 text-[9px] font-bold transition-colors ${location === city ? 'border-amber-500/30 bg-amber-500/10 text-amber-500' : 'border-white/10 bg-black/30 text-white/40 hover:text-white/60 hover:border-white/20'}`}
                  >
                    {city.length > 25 ? city.slice(0, 22) + '...' : city}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Job Cards Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {loading
          ? Array.from({ length: 9 }).map((_, i) => (
              <div
                key={`skel-${i}`}
                className="flex flex-col gap-4 rounded-2xl border border-white/5 bg-[#0A0A0A] p-6"
              >
                <div className="flex items-start justify-between">
                  <div className="h-6 w-3/4 rounded bg-white/5 shimmer"></div>
                  <div className="h-6 w-12 rounded bg-white/5 shimmer"></div>
                </div>
                <div className="space-y-2">
                  <div className="h-4 w-1/2 rounded bg-white/5 shimmer"></div>
                  <div className="h-4 w-1/3 rounded bg-white/5 shimmer"></div>
                  <div className="h-10 w-full rounded bg-white/5 shimmer mt-2"></div>
                </div>
              </div>
            ))
          : jobs.length === 0
            ? (
                <div className="col-span-full py-32 text-center">
                  <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-white/5">
                    <Radar className="h-8 w-8 text-white/20" />
                  </div>
                  <p className="text-sm font-black uppercase tracking-[0.2em] text-white/40">
                    No jobs discovered yet
                  </p>
                  <p className="mt-2 text-xs text-white/20">
                    Click "Discover Jobs" to scan all platforms
                  </p>
                </div>
              )
            : jobs.map((job) => (
                <div
                  key={job.id}
                  className="group flex flex-col justify-between rounded-2xl border border-white/5 bg-[#0A0A0A] p-5 transition-all hover:-translate-y-1 hover:border-white/10 hover:bg-white/[0.02] hover:shadow-2xl cursor-pointer"
                  onClick={() => openDetail(job)}
                >
                  <div>
                    {/* Platform badges + time */}
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <div className="flex flex-wrap gap-1">
                        {(job.platforms_seen || [job.platform]).map((p: string) => (
                          <span
                            key={p}
                            className={`rounded border px-2 py-0.5 text-[8px] font-black uppercase tracking-wider ${PLATFORM_META[p]?.color || 'border-white/10 bg-white/5 text-white/30'}`}
                          >
                            {PLATFORM_META[p]?.label || p}
                          </span>
                        ))}
                      </div>
                      {job.posted_at && (
                        <span className="flex items-center gap-1 text-[9px] text-white/30 shrink-0">
                          <Clock className="h-2.5 w-2.5" />
                          {timeAgo(job.posted_at)}
                        </span>
                      )}
                    </div>

                    {/* Title */}
                    <h3 className="line-clamp-2 text-sm font-bold leading-tight text-white/90 transition-colors group-hover:text-white mb-2">
                      {job.title}
                    </h3>

                    {/* Company + Location */}
                    <div className="space-y-1.5 text-xs text-white/40">
                      <div className="flex items-center gap-2">
                        <Building2 className="h-3 w-3 shrink-0 text-white/20" />
                        <span className="truncate">{job.company || 'Unknown'}</span>
                      </div>
                      {job.location && (
                        <div className="flex items-center gap-2">
                          <MapPin className="h-3 w-3 shrink-0 text-white/20" />
                          <span className="truncate">{job.location}</span>
                        </div>
                      )}
                    </div>

                    {/* Badges row */}
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {job.remote && (
                        <span className="rounded border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold text-emerald-400">
                          Remote
                        </span>
                      )}
                      {job.employment_type && (
                        <span className="rounded border border-white/10 bg-white/5 px-2 py-0.5 text-[9px] font-bold text-white/50">
                          {job.employment_type}
                        </span>
                      )}
                      {job.salary_text && (
                        <span className="rounded border border-amber-500/20 bg-amber-500/5 px-2 py-0.5 text-[9px] font-bold text-amber-400">
                          {job.salary_text}
                        </span>
                      )}
                    </div>

                    {/* Description preview */}
                    {job.description_preview && (
                      <p className="mt-3 line-clamp-2 text-[11px] leading-relaxed text-white/25">
                        {job.description_preview}
                      </p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="mt-4 flex gap-2 pt-3 border-t border-white/5">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleApply(job)
                      }}
                      disabled={applying === job.id}
                      className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-amber-500 px-4 py-2.5 text-[10px] font-black uppercase tracking-wider text-black shadow-lg shadow-amber-500/20 transition-all hover:bg-amber-400 active:scale-95 disabled:opacity-50"
                    >
                      {applying === job.id ? (
                        <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-black border-t-transparent" />
                      ) : (
                        <>
                          <Zap className="h-3 w-3" />
                          Apply
                        </>
                      )}
                    </button>
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="flex items-center justify-center rounded-xl border border-white/10 bg-white/5 p-2.5 text-white/40 transition-all hover:border-white/20 hover:bg-white/10 hover:text-white"
                      title="Open original posting"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </div>
                </div>
              ))}
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-center gap-4 pt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-xl border border-white/10 bg-[#0A0A0A] px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-white/60 transition-all hover:bg-white/5 hover:text-white disabled:opacity-30"
          >
            Previous
          </button>
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/20">
            Page <span className="text-amber-500">{page}</span> of {Math.ceil(total / 20)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 20)}
            className="rounded-xl border border-white/10 bg-[#0A0A0A] px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-white/60 transition-all hover:bg-white/5 hover:text-white disabled:opacity-30"
          >
            Next
          </button>
        </div>
      )}

      {/* Job Detail Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setSelectedJob(null)} />
          <div className="relative max-w-2xl w-full max-h-[85vh] overflow-auto rounded-2xl border border-white/10 bg-[#0A0A0A] shadow-2xl">
            {/* Modal Header */}
            <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-white/5 bg-[#0A0A0A]/95 backdrop-blur-xl p-6">
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {(selectedJob.platforms_seen || [selectedJob.platform]).map((p: string) => (
                    <span
                      key={p}
                      className={`rounded border px-2 py-0.5 text-[8px] font-black uppercase tracking-wider ${PLATFORM_META[p]?.color || 'border-white/10 bg-white/5 text-white/30'}`}
                    >
                      {PLATFORM_META[p]?.label || p}
                    </span>
                  ))}
                </div>
                <h2 className="text-lg font-bold text-white">{selectedJob.title}</h2>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-white/40">
                  <span className="flex items-center gap-1.5">
                    <Building2 className="h-3.5 w-3.5" />
                    {selectedJob.company || 'Unknown'}
                  </span>
                  {selectedJob.location && (
                    <span className="flex items-center gap-1.5">
                      <MapPin className="h-3.5 w-3.5" />
                      {selectedJob.location}
                    </span>
                  )}
                  {selectedJob.posted_at && (
                    <span className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5" />
                      {timeAgo(selectedJob.posted_at)}
                    </span>
                  )}
                </div>
                {/* Badges */}
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {selectedJob.remote && (
                    <span className="rounded border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[9px] font-bold text-emerald-400">
                      Remote
                    </span>
                  )}
                  {selectedJob.employment_type && (
                    <span className="rounded border border-white/10 bg-white/5 px-2 py-0.5 text-[9px] font-bold text-white/50">
                      {selectedJob.employment_type}
                    </span>
                  )}
                  {selectedJob.salary_text && (
                    <span className="rounded border border-amber-500/20 bg-amber-500/5 px-2 py-0.5 text-[9px] font-bold text-amber-400">
                      {selectedJob.salary_text}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => setSelectedJob(null)}
                className="shrink-0 rounded-lg border border-white/10 p-2 text-white/30 hover:bg-white/5 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              {detailLoading ? (
                <div className="space-y-3">
                  <div className="h-4 w-full rounded bg-white/5 shimmer" />
                  <div className="h-4 w-5/6 rounded bg-white/5 shimmer" />
                  <div className="h-4 w-4/6 rounded bg-white/5 shimmer" />
                </div>
              ) : selectedJob.description ? (
                <div className="prose prose-invert prose-sm max-w-none text-white/60 leading-relaxed text-sm whitespace-pre-line">
                  {selectedJob.description}
                </div>
              ) : (
                <p className="text-sm text-white/30 italic">
                  No description available. Click "Apply on Platform" to view the full listing.
                </p>
              )}
            </div>

            {/* Modal Footer */}
            <div className="sticky bottom-0 flex items-center gap-3 border-t border-white/5 bg-[#0A0A0A]/95 backdrop-blur-xl p-6">
              <a
                href={selectedJob.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-amber-500 py-3.5 text-sm font-black uppercase tracking-wider text-black transition-all hover:bg-amber-400"
              >
                <ExternalLink className="h-4 w-4" />
                Apply on {PLATFORM_META[selectedJob.platform]?.label || selectedJob.platform}
              </a>
              <button
                onClick={() => {
                  handleApply(selectedJob)
                  setSelectedJob(null)
                }}
                className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-6 py-3.5 text-sm font-bold text-white/60 transition-all hover:bg-white/10 hover:text-white"
              >
                <Briefcase className="h-4 w-4" />
                Log Applied
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
