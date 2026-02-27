import { useState, useEffect } from 'react'
import { api } from '../api'

const STATUSES = ['', 'pending', 'applying', 'success', 'failed', 'skipped', 'external']
const RESPONSES = ['', 'waiting', 'interview', 'rejected', 'ghosted', 'offer']

export default function Applications() {
  const [apps, setApps] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [sourceFilter, setSourceFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [responseFilter, setResponseFilter] = useState('')
  const [platformFilter, setPlatformFilter] = useState('')

  const fetchApps = async () => {
    const params: Record<string, any> = { page: String(page), per_page: '25' }
    if (sourceFilter) params.source = sourceFilter
    if (statusFilter) params.status = statusFilter
    if (responseFilter) params.response_status = responseFilter
    if (platformFilter) params.platform = platformFilter
    const res = await api.getApplications(params)
    setApps(res.applications || [])
    setTotal(res.total || 0)
  }

  useEffect(() => {
    fetchApps()
  }, [page, sourceFilter, statusFilter, responseFilter, platformFilter])

  const updateResponse = async (id: number, response_status: string) => {
    await api.updateResponse(id, { response_status })
    fetchApps()
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
            <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" strokeWidth="2.5" />
          </svg>
        </div>
        <span className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">
          Applications
        </span>
        <span className="ml-auto text-[10px] font-black uppercase tracking-wider text-white/20">
          {total} records
        </span>
      </div>

      {/* Source tabs */}
      <div className="flex gap-1 rounded-xl border border-white/5 bg-[#0A0A0A] p-1">
        {[
          { value: '', label: 'All' },
          { value: 'bot', label: 'Bot Applied' },
          { value: 'external', label: 'External' },
        ].map(({ value, label }) => (
          <button
            key={value}
            onClick={() => {
              setSourceFilter(value)
              setPage(1)
            }}
            className={`rounded-lg px-4 py-2 text-[10px] font-black uppercase tracking-[0.15em] transition-colors ${
              sourceFilter === value
                ? value === 'external'
                  ? 'bg-purple-500/20 text-purple-400'
                  : 'bg-amber-500/20 text-amber-500'
                : 'text-white/30 hover:text-white/50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        {[
          { value: statusFilter, setter: setStatusFilter, options: STATUSES, label: 'Status' },
          {
            value: responseFilter,
            setter: setResponseFilter,
            options: RESPONSES,
            label: 'Response',
          },
        ].map(({ value, setter, options, label }) => (
          <select
            key={label}
            value={value}
            onChange={(e) => {
              setter(e.target.value)
              setPage(1)
            }}
            className="rounded-xl border border-white/5 bg-[#0A0A0A] px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-white/40 focus:outline-none"
          >
            <option value="">All {label}s</option>
            {options.filter(Boolean).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        ))}
        <select
          value={platformFilter}
          onChange={(e) => {
            setPlatformFilter(e.target.value)
            setPage(1)
          }}
          className="rounded-xl border border-white/5 bg-[#0A0A0A] px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-white/40 focus:outline-none"
        >
          <option value="">All Platforms</option>
          <option value="stepstone">StepStone</option>
          <option value="xing">Xing</option>
          <option value="linkedin">LinkedIn</option>
          <option value="indeed">Indeed</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-xl border border-white/5 bg-[#0A0A0A]">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              {['Title', 'Company', 'Platform', 'Status', 'Response', 'Date', ''].map((h) => (
                <th
                  key={h}
                  className="px-5 py-3 text-left text-[8px] font-black uppercase tracking-[0.2em] text-white/15"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="font-mono text-[12px]">
            {apps.map((a) => (
              <tr
                key={a.id}
                className="border-b border-white/[0.03] transition-colors hover:bg-white/[0.02]"
              >
                <td className="max-w-[220px] truncate px-5 py-3 text-white/60">
                  {a.job_title || '-'}
                </td>
                <td className="px-5 py-3 text-white/30">{a.company || '-'}</td>
                <td className="px-5 py-3">
                  <span
                    className={`rounded border px-2 py-0.5 text-[8px] font-black uppercase tracking-wider ${
                      a.platform === 'stepstone'
                        ? 'border-amber-500/20 bg-amber-500/10 text-amber-500'
                        : a.platform === 'xing'
                          ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
                          : a.platform === 'linkedin'
                            ? 'border-blue-500/20 bg-blue-500/10 text-blue-400'
                            : a.platform === 'indeed'
                              ? 'border-purple-500/20 bg-purple-500/10 text-purple-400'
                              : 'border-white/10 bg-white/5 text-white/30'
                    }`}
                  >
                    {a.platform}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <span
                    className={`rounded border px-2 py-0.5 text-[8px] font-black uppercase tracking-wider ${
                      a.status === 'success'
                        ? 'border-[#27C93F]/20 bg-[#27C93F]/10 text-[#27C93F]'
                        : a.status === 'failed'
                          ? 'border-red-500/20 bg-red-500/10 text-red-400'
                          : a.status === 'pending'
                            ? 'border-amber-500/20 bg-amber-500/10 text-amber-500'
                            : a.status === 'external'
                              ? 'border-purple-500/20 bg-purple-500/10 text-purple-400'
                              : 'border-white/10 bg-white/5 text-white/30'
                    }`}
                  >
                    {a.status}
                  </span>
                </td>
                <td className="px-5 py-3">
                  <select
                    value={a.response_status || 'waiting'}
                    onChange={(e) => updateResponse(a.id, e.target.value)}
                    className="rounded-lg border border-white/5 bg-transparent px-2 py-1 text-[10px] font-bold text-white/30 focus:border-amber-500/30 focus:outline-none"
                  >
                    {RESPONSES.filter(Boolean).map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-5 py-3 text-[10px] text-white/15">
                  {a.applied_at?.split('T')[0] || '-'}
                </td>
                <td className="px-5 py-3">
                  {a.url && (
                    <a
                      href={a.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`text-[10px] font-bold uppercase tracking-wider transition-colors ${
                        a.status === 'external'
                          ? 'rounded border border-purple-500/20 bg-purple-500/10 px-2 py-1 text-purple-400 hover:text-purple-300'
                          : 'text-white/15 hover:text-amber-500'
                      }`}
                    >
                      {a.status === 'external' ? 'Apply →' : 'Open'}
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > 25 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-lg border border-white/5 bg-white/5 px-4 py-2 text-[10px] font-bold text-white/40 disabled:opacity-20"
          >
            Prev
          </button>
          <span className="px-4 py-2 text-[10px] font-black text-white/20">Page {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 25)}
            className="rounded-lg border border-white/5 bg-white/5 px-4 py-2 text-[10px] font-bold text-white/40 disabled:opacity-20"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
