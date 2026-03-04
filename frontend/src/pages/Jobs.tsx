import React, { useState, useEffect } from 'react'
import { Search, MapPin, Building2, ExternalLink, Briefcase, Zap, CheckCircle2 } from 'lucide-react'
import { api } from '../api'

export default function Jobs() {
  const [jobs, setJobs] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [location, setLocation] = useState('')
  const [platform, setPlatform] = useState('')
  const [applying, setApplying] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<{show: boolean, msg: string}>({ show: false, msg: '' })

  const fetchJobs = async () => {
    setLoading(true)
    const params: Record<string, any> = { page: String(page), per_page: '20' }
    if (search) params.search = search
    if (location) params.location = location
    if (platform) params.platform = platform
    const res = await api.getJobs(params)
    setJobs(res.jobs || [])
    setTotal(res.total || 0)
    setLoading(false)
  }

  useEffect(() => { fetchJobs() }, [page, platform])

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); setPage(1); fetchJobs() }

  const handleApply = async (job: any) => {
    setApplying(job.id)
    await api.manualApply({ job_id: job.id, platform: job.platform, job_title: job.title, company: job.company, url: job.url })
    window.open(job.url, '_blank')
    setApplying(null)
    setToast({ show: true, msg: 'Application initiated' })
    setTimeout(() => setToast({ show: false, msg: '' }), 3000)
    fetchJobs()
  }

  const platformColors: Record<string, string> = {
    stepstone: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
    xing: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    linkedin: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    indeed: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  }

  return (
    <div className="space-y-6 sm:space-y-8 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto relative">
      <div className={`fixed top-[60px] md:top-8 right-4 sm:right-8 left-4 sm:left-auto z-50 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm font-bold text-emerald-400 shadow-2xl backdrop-blur-md transition-all duration-300 ${toast.show ? 'translate-y-0 opacity-100' : '-translate-y-4 opacity-0 pointer-events-none'}`}>
        <CheckCircle2 className="h-4 w-4" />{toast.msg}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
            <Search className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Discovery</h1>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">Target Acquisition</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-[#0A0A0A] px-4 py-2 shadow-lg">
          <span className="text-[10px] font-black uppercase tracking-wider text-white/40">Targets Found</span>
          <span className="text-sm font-bold text-amber-500">{total}</span>
        </div>
      </div>

      <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-4 rounded-2xl border border-white/10 bg-[#0A0A0A] p-4 shadow-2xl">
        <div className="relative flex-1 group">
          <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-white/20 transition-colors group-focus-within:text-amber-500" />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by title or company..." className="w-full rounded-xl border border-white/5 bg-black/50 pl-12 pr-4 py-4 text-sm text-white transition-all placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50" />
        </div>
        <div className="relative sm:w-64 group">
          <MapPin className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-white/20 transition-colors group-focus-within:text-amber-500" />
          <input type="text" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="Location..." className="w-full rounded-xl border border-white/5 bg-black/50 pl-12 pr-4 py-4 text-sm text-white transition-all placeholder:text-white/20 focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50" />
        </div>
        <div className="relative sm:w-48 group">
          <Briefcase className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-white/20 transition-colors group-focus-within:text-amber-500" />
          <select value={platform} onChange={(e) => { setPlatform(e.target.value); setPage(1) }} className="w-full appearance-none rounded-xl border border-white/5 bg-black/50 pl-12 pr-4 py-4 text-sm font-bold uppercase tracking-wider text-white/60 transition-all focus:border-amber-500/50 focus:bg-black focus:outline-none focus:ring-1 focus:ring-amber-500/50">
            <option value="">All Platforms</option>
            <option value="stepstone">StepStone</option>
            <option value="xing">Xing</option>
            <option value="linkedin">LinkedIn</option>
            <option value="indeed">Indeed</option>
          </select>
        </div>
        <button type="submit" className="group relative flex items-center justify-center gap-2 overflow-hidden rounded-xl bg-amber-500 px-8 py-4 text-sm font-black uppercase tracking-wider text-black shadow-[0_0_20px_rgba(245,158,11,0.2)] transition-all hover:scale-[1.02] hover:bg-amber-400 hover:shadow-[0_0_30px_rgba(245,158,11,0.4)] active:scale-[0.98]">
          <div className="absolute inset-0 flex h-full w-full justify-center [transform:skew(-12deg)_translateX(-100%)] group-hover:duration-1000 group-hover:[transform:skew(-12deg)_translateX(100%)]"><div className="relative h-full w-8 bg-white/20" /></div>
          <span className="relative">Scan</span>
        </button>
      </form>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {loading ? Array.from({ length: 9 }).map((_, i) => (
          <div key={`skeleton-${i}`} className="flex flex-col gap-4 rounded-2xl border border-white/5 bg-[#0A0A0A] p-6">
            <div className="flex items-start justify-between"><div className="h-6 w-3/4 rounded bg-white/5 shimmer"></div><div className="h-6 w-12 rounded bg-white/5 shimmer"></div></div>
            <div className="space-y-2"><div className="h-4 w-1/2 rounded bg-white/5 shimmer"></div><div className="h-4 w-1/3 rounded bg-white/5 shimmer"></div></div>
            <div className="mt-auto pt-4 flex gap-2"><div className="h-10 w-full rounded-xl bg-white/5 shimmer"></div><div className="h-10 w-12 rounded-xl bg-white/5 shimmer"></div></div>
          </div>
        )) : jobs.length === 0 ? (
          <div className="col-span-full py-32 text-center">
            <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-white/5"><Search className="h-8 w-8 text-white/20" /></div>
            <p className="text-sm font-black uppercase tracking-[0.2em] text-white/40">No targets detected</p>
            <p className="mt-2 text-xs text-white/20">Adjust your search parameters or run a new scrape cycle</p>
          </div>
        ) : jobs.map((job) => (
          <div key={job.id} className="group flex flex-col justify-between rounded-2xl border border-white/5 bg-[#0A0A0A] p-6 transition-all hover:-translate-y-1 hover:border-white/10 hover:bg-white/[0.02] hover:shadow-2xl">
            <div>
              <div className="mb-4 flex items-start justify-between gap-4">
                <h3 className="line-clamp-2 text-base font-bold leading-tight text-white/90 transition-colors group-hover:text-white">{job.title}</h3>
                <div className={`shrink-0 rounded-lg border px-2.5 py-1 text-[9px] font-black uppercase tracking-wider ${platformColors[job.platform] || 'border-white/10 bg-white/5 text-white/30'}`}>{job.platform}</div>
              </div>
              <div className="space-y-2 text-xs text-white/40">
                <div className="flex items-center gap-2"><Building2 className="h-3.5 w-3.5 shrink-0 text-white/20" /><span className="truncate">{job.company}</span></div>
                {job.location && <div className="flex items-center gap-2"><MapPin className="h-3.5 w-3.5 shrink-0 text-white/20" /><span className="truncate">{job.location}</span></div>}
              </div>
            </div>
            <div className="mt-6 flex gap-2 pt-4 border-t border-white/5">
              <button onClick={() => handleApply(job)} disabled={applying === job.id} className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-amber-500 px-4 py-3 text-[10px] font-black uppercase tracking-wider text-black shadow-lg shadow-amber-500/20 transition-all hover:bg-amber-400 hover:shadow-amber-500/40 active:scale-95 disabled:opacity-50">
                {applying === job.id ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-black border-t-transparent" /> : <><Zap className="h-3.5 w-3.5" />Apply Now</>}
              </button>
              <a href={job.url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-center rounded-xl border border-white/10 bg-white/5 p-3 text-white/40 transition-all hover:border-white/20 hover:bg-white/10 hover:text-white" title="View Original Posting"><ExternalLink className="h-4 w-4" /></a>
            </div>
          </div>
        ))}
      </div>

      {total > 20 && (
        <div className="flex items-center justify-center gap-4 pt-8">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="rounded-xl border border-white/10 bg-[#0A0A0A] px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-white/60 transition-all hover:bg-white/5 hover:text-white disabled:opacity-30">Previous</button>
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/20">Page <span className="text-amber-500">{page}</span> of {Math.ceil(total / 20)}</span>
          <button onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(total / 20)} className="rounded-xl border border-white/10 bg-[#0A0A0A] px-6 py-3 text-[10px] font-bold uppercase tracking-wider text-white/60 transition-all hover:bg-white/5 hover:text-white disabled:opacity-30">Next</button>
        </div>
      )}
    </div>
  )
}
