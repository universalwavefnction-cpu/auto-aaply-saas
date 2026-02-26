import { useState, useEffect } from 'react'
import { api } from '../api'

const STATUSES = ['', 'pending', 'applying', 'success', 'failed', 'skipped']
const RESPONSES = ['', 'waiting', 'interview', 'rejected', 'ghosted', 'offer']

export default function Applications() {
  const [apps, setApps] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [responseFilter, setResponseFilter] = useState('')
  const [platformFilter, setPlatformFilter] = useState('')

  const fetchApps = async () => {
    const params: Record<string, any> = { page: String(page), per_page: '25' }
    if (statusFilter) params.status = statusFilter
    if (responseFilter) params.response_status = responseFilter
    if (platformFilter) params.platform = platformFilter
    const res = await api.getApplications(params)
    setApps(res.applications || [])
    setTotal(res.total || 0)
  }

  useEffect(() => { fetchApps() }, [page, statusFilter, responseFilter, platformFilter])

  const updateResponse = async (id: number, response_status: string) => {
    await api.updateResponse(id, { response_status })
    fetchApps()
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-1.5 bg-amber-500/10 rounded-md">
          <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" strokeWidth="2.5"/>
          </svg>
        </div>
        <span className="uppercase font-black tracking-[0.2em] text-[11px] text-white/60">Applications</span>
        <span className="ml-auto text-[10px] font-black text-white/20 uppercase tracking-wider">{total} records</span>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        {[
          { value: statusFilter, setter: setStatusFilter, options: STATUSES, label: 'Status' },
          { value: responseFilter, setter: setResponseFilter, options: RESPONSES, label: 'Response' },
        ].map(({ value, setter, options, label }) => (
          <select key={label} value={value} onChange={e => { setter(e.target.value); setPage(1) }}
            className="px-4 py-2.5 bg-[#0A0A0A] border border-white/5 rounded-xl text-[10px] font-bold text-white/40 uppercase tracking-wider focus:outline-none">
            <option value="">All {label}s</option>
            {options.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        ))}
        <select value={platformFilter} onChange={e => { setPlatformFilter(e.target.value); setPage(1) }}
          className="px-4 py-2.5 bg-[#0A0A0A] border border-white/5 rounded-xl text-[10px] font-bold text-white/40 uppercase tracking-wider focus:outline-none">
          <option value="">All Platforms</option>
          <option value="stepstone">StepStone</option>
          <option value="xing">Xing</option>
          <option value="linkedin">LinkedIn</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-[#0A0A0A] border border-white/5 rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              {['Title', 'Company', 'Platform', 'Status', 'Response', 'Date', ''].map(h => (
                <th key={h} className="text-left px-5 py-3 text-[8px] font-black text-white/15 uppercase tracking-[0.2em]">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="font-mono text-[12px]">
            {apps.map(a => (
              <tr key={a.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                <td className="px-5 py-3 max-w-[220px] truncate text-white/60">{a.job_title || '-'}</td>
                <td className="px-5 py-3 text-white/30">{a.company || '-'}</td>
                <td className="px-5 py-3">
                  <span className={`px-2 py-0.5 rounded text-[8px] font-black border uppercase tracking-wider ${
                    a.platform === 'stepstone' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' :
                    a.platform === 'xing' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                    'bg-white/5 text-white/30 border-white/10'
                  }`}>{a.platform}</span>
                </td>
                <td className="px-5 py-3">
                  <span className={`px-2 py-0.5 rounded text-[8px] font-black border uppercase tracking-wider ${
                    a.status === 'success' ? 'bg-[#27C93F]/10 text-[#27C93F] border-[#27C93F]/20' :
                    a.status === 'failed' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                    a.status === 'pending' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' :
                    'bg-white/5 text-white/30 border-white/10'
                  }`}>{a.status}</span>
                </td>
                <td className="px-5 py-3">
                  <select
                    value={a.response_status || 'waiting'}
                    onChange={e => updateResponse(a.id, e.target.value)}
                    className="bg-transparent text-[10px] font-bold text-white/30 border border-white/5 rounded-lg px-2 py-1 focus:outline-none focus:border-amber-500/30"
                  >
                    {RESPONSES.filter(Boolean).map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td className="px-5 py-3 text-white/15 text-[10px]">{a.applied_at?.split('T')[0] || '-'}</td>
                <td className="px-5 py-3">
                  {a.url && (
                    <a href={a.url} target="_blank" rel="noopener noreferrer"
                      className="text-white/15 hover:text-amber-500 transition-colors text-[10px] font-bold uppercase tracking-wider">
                      Open
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
        <div className="flex gap-2 justify-center">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="px-4 py-2 bg-white/5 border border-white/5 rounded-lg text-[10px] font-bold text-white/40 disabled:opacity-20">Prev</button>
          <span className="px-4 py-2 text-[10px] font-black text-white/20">Page {page}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / 25)}
            className="px-4 py-2 bg-white/5 border border-white/5 rounded-lg text-[10px] font-bold text-white/40 disabled:opacity-20">Next</button>
        </div>
      )}
    </div>
  )
}
