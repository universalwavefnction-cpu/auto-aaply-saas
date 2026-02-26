import { useState, useEffect } from 'react'
import { api } from '../api'

export default function Jobs() {
  const [jobs, setJobs] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [location, setLocation] = useState('')
  const [platform, setPlatform] = useState('')
  const [applying, setApplying] = useState<number | null>(null)

  const fetchJobs = async () => {
    const params: Record<string, any> = { page: String(page), per_page: '20' }
    if (search) params.search = search
    if (location) params.location = location
    if (platform) params.platform = platform
    const res = await api.getJobs(params)
    setJobs(res.jobs || [])
    setTotal(res.total || 0)
  }

  useEffect(() => { fetchJobs() }, [page, platform])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    fetchJobs()
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
    fetchJobs()
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-1.5 bg-amber-500/10 rounded-md">
          <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeWidth="2.5"/>
          </svg>
        </div>
        <span className="uppercase font-black tracking-[0.2em] text-[11px] text-white/60">Job Discovery</span>
        <span className="ml-auto text-[10px] font-black text-white/20 uppercase tracking-wider">{total} targets found</span>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="flex-1 relative">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by title or company..."
            className="w-full px-4 py-3 bg-[#0A0A0A] border border-white/5 rounded-xl text-sm text-white placeholder:text-white/15 focus:outline-none focus:border-amber-500/30 transition-colors"
          />
        </div>
        <input
          type="text"
          value={location}
          onChange={e => setLocation(e.target.value)}
          placeholder="Location..."
          className="w-48 px-4 py-3 bg-[#0A0A0A] border border-white/5 rounded-xl text-sm text-white placeholder:text-white/15 focus:outline-none focus:border-amber-500/30 transition-colors"
        />
        <select
          value={platform}
          onChange={e => { setPlatform(e.target.value); setPage(1) }}
          className="px-4 py-3 bg-[#0A0A0A] border border-white/5 rounded-xl text-sm text-white/60 focus:outline-none"
        >
          <option value="">All Platforms</option>
          <option value="stepstone">StepStone</option>
          <option value="xing">Xing</option>
          <option value="linkedin">LinkedIn</option>
        </select>
        <button type="submit" className="px-6 py-3 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-sm font-black shadow-lg shadow-amber-500/20 transition-all">
          Scan
        </button>
      </form>

      {/* Job Cards */}
      <div className="space-y-3">
        {jobs.map(job => {
          const platformColors: Record<string, string> = {
            stepstone: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
            xing: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
            linkedin: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
          }
          return (
            <div key={job.id} className="bg-[#0A0A0A] border border-white/5 rounded-xl p-5 flex items-center gap-6 hover:border-white/10 transition-colors group">
              {/* Platform badge */}
              <div className={`shrink-0 px-2.5 py-1 rounded-lg border text-[8px] font-black uppercase tracking-wider ${platformColors[job.platform] || 'bg-white/5 text-white/30 border-white/10'}`}>
                {job.platform}
              </div>

              {/* Job info */}
              <div className="flex-1 min-w-0">
                <h3 className="font-bold text-sm text-white/80 group-hover:text-white transition-colors truncate">{job.title}</h3>
                <div className="flex gap-4 mt-1">
                  <span className="text-[10px] text-white/30 font-bold">{job.company}</span>
                  {job.location && <span className="text-[10px] text-white/20">{job.location}</span>}
                  {job.salary_min && <span className="text-[10px] text-amber-500/60">{job.salary_min.toLocaleString()}-{job.salary_max?.toLocaleString()}</span>}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 shrink-0">
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-2 bg-white/5 border border-white/5 rounded-lg text-[9px] font-black text-white/40 uppercase tracking-wider hover:text-white/70 hover:border-white/10 transition-colors"
                >
                  View
                </a>
                <button
                  onClick={() => handleApply(job)}
                  disabled={applying === job.id}
                  className="px-4 py-2 bg-amber-500 hover:bg-amber-600 rounded-lg text-[9px] font-black text-white uppercase tracking-wider shadow-lg shadow-amber-500/20 transition-all hover:scale-105 active:scale-100 disabled:opacity-50"
                >
                  {applying === job.id ? 'Applying...' : 'Apply Now'}
                </button>
              </div>
            </div>
          )
        })}

        {jobs.length === 0 && (
          <div className="text-center py-20">
            <p className="text-white/15 text-[11px] font-black uppercase tracking-[0.2em]">No targets detected</p>
            <p className="text-white/10 text-[10px] mt-2">Run a scrape cycle to discover new jobs</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex gap-2 justify-center">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="px-4 py-2 bg-white/5 border border-white/5 rounded-lg text-[10px] font-bold text-white/40 disabled:opacity-20 hover:text-white/60 transition-colors">
            Prev
          </button>
          <span className="px-4 py-2 text-[10px] font-black text-white/20 uppercase tracking-wider">
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 20)}
            className="px-4 py-2 bg-white/5 border border-white/5 rounded-lg text-[10px] font-bold text-white/40 disabled:opacity-20 hover:text-white/60 transition-colors">
            Next
          </button>
        </div>
      )}
    </div>
  )
}
