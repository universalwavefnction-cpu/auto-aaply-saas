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

  useEffect(() => {
    fetchJobs()
  }, [page, platform])

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
    <div className="space-y-6 p-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="rounded-md bg-amber-500/10 p-1.5">
          <svg
            className="h-4 w-4 text-amber-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              strokeLinecap="round"
              strokeWidth="2.5"
            />
          </svg>
        </div>
        <span className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">
          Job Discovery
        </span>
        <span className="ml-auto text-[10px] font-black uppercase tracking-wider text-white/20">
          {total} targets found
        </span>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title or company..."
            className="w-full rounded-xl border border-white/5 bg-[#0A0A0A] px-4 py-3 text-sm text-white transition-colors placeholder:text-white/15 focus:border-amber-500/30 focus:outline-none"
          />
        </div>
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="Location..."
          className="w-48 rounded-xl border border-white/5 bg-[#0A0A0A] px-4 py-3 text-sm text-white transition-colors placeholder:text-white/15 focus:border-amber-500/30 focus:outline-none"
        />
        <select
          value={platform}
          onChange={(e) => {
            setPlatform(e.target.value)
            setPage(1)
          }}
          className="rounded-xl border border-white/5 bg-[#0A0A0A] px-4 py-3 text-sm text-white/60 focus:outline-none"
        >
          <option value="">All Platforms</option>
          <option value="stepstone">StepStone</option>
          <option value="xing">Xing</option>
          <option value="linkedin">LinkedIn</option>
        </select>
        <button
          type="submit"
          className="rounded-xl bg-amber-500 px-6 py-3 text-sm font-black text-white shadow-lg shadow-amber-500/20 transition-all hover:bg-amber-600"
        >
          Scan
        </button>
      </form>

      {/* Job Cards */}
      <div className="space-y-3">
        {jobs.map((job) => {
          const platformColors: Record<string, string> = {
            stepstone: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
            xing: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
            linkedin: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
          }
          return (
            <div
              key={job.id}
              className="group flex items-center gap-6 rounded-xl border border-white/5 bg-[#0A0A0A] p-5 transition-colors hover:border-white/10"
            >
              {/* Platform badge */}
              <div
                className={`shrink-0 rounded-lg border px-2.5 py-1 text-[8px] font-black uppercase tracking-wider ${platformColors[job.platform] || 'border-white/10 bg-white/5 text-white/30'}`}
              >
                {job.platform}
              </div>

              {/* Job info */}
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-sm font-bold text-white/80 transition-colors group-hover:text-white">
                  {job.title}
                </h3>
                <div className="mt-1 flex gap-4">
                  <span className="text-[10px] font-bold text-white/30">{job.company}</span>
                  {job.location && (
                    <span className="text-[10px] text-white/20">{job.location}</span>
                  )}
                  {job.salary_min && (
                    <span className="text-[10px] text-amber-500/60">
                      {job.salary_min.toLocaleString()}-{job.salary_max?.toLocaleString()}
                    </span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex shrink-0 gap-2">
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-lg border border-white/5 bg-white/5 px-3 py-2 text-[9px] font-black uppercase tracking-wider text-white/40 transition-colors hover:border-white/10 hover:text-white/70"
                >
                  View
                </a>
                <button
                  onClick={() => handleApply(job)}
                  disabled={applying === job.id}
                  className="rounded-lg bg-amber-500 px-4 py-2 text-[9px] font-black uppercase tracking-wider text-white shadow-lg shadow-amber-500/20 transition-all hover:scale-105 hover:bg-amber-600 active:scale-100 disabled:opacity-50"
                >
                  {applying === job.id ? 'Applying...' : 'Apply Now'}
                </button>
              </div>
            </div>
          )
        })}

        {jobs.length === 0 && (
          <div className="py-20 text-center">
            <p className="text-[11px] font-black uppercase tracking-[0.2em] text-white/15">
              No targets detected
            </p>
            <p className="mt-2 text-[10px] text-white/10">
              Run a scrape cycle to discover new jobs
            </p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-lg border border-white/5 bg-white/5 px-4 py-2 text-[10px] font-bold text-white/40 transition-colors hover:text-white/60 disabled:opacity-20"
          >
            Prev
          </button>
          <span className="px-4 py-2 text-[10px] font-black uppercase tracking-wider text-white/20">
            Page {page} of {Math.ceil(total / 20)}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 20)}
            className="rounded-lg border border-white/5 bg-white/5 px-4 py-2 text-[10px] font-bold text-white/40 transition-colors hover:text-white/60 disabled:opacity-20"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
