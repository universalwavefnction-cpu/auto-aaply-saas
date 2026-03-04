import { useState, useEffect } from 'react'
import { Send, Filter, ChevronLeft, ChevronRight, ExternalLink, CheckCircle2 } from 'lucide-react'
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
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<{show: boolean, msg: string}>({ show: false, msg: '' })

  const fetchApps = async () => {
    setLoading(true)
    const params: Record<string, any> = { page: String(page), per_page: '25' }
    if (sourceFilter) params.source = sourceFilter
    if (statusFilter) params.status = statusFilter
    if (responseFilter) params.response_status = responseFilter
    if (platformFilter) params.platform = platformFilter
    const res = await api.getApplications(params)
    setApps(res.applications || [])
    setTotal(res.total || 0)
    setLoading(false)
  }

  useEffect(() => { fetchApps() }, [page, sourceFilter, statusFilter, responseFilter, platformFilter])

  const updateResponse = async (id: number, response_status: string) => {
    await api.updateResponse(id, { response_status })
    setToast({ show: true, msg: 'Response status updated' })
    setTimeout(() => setToast({ show: false, msg: '' }), 3000)
    fetchApps()
  }

  return (
    <div className="space-y-6 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto relative">
      <div className={`fixed top-[60px] md:top-8 right-4 sm:right-8 left-4 sm:left-auto z-50 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm font-bold text-emerald-400 shadow-2xl backdrop-blur-md transition-all duration-300 ${toast.show ? 'translate-y-0 opacity-100' : '-translate-y-4 opacity-0 pointer-events-none'}`}><CheckCircle2 className="h-4 w-4" />{toast.msg}</div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20"><Send className="h-5 w-5 text-amber-500" /></div>
          <div><h1 className="text-2xl font-bold tracking-tight text-white">Applications</h1><p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">Track & Manage</p></div>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-[#0A0A0A] px-4 py-2"><span className="text-[10px] font-black uppercase tracking-wider text-white/40">Total Records</span><span className="text-sm font-bold text-amber-500">{total}</span></div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex gap-1 rounded-xl border border-white/10 bg-[#0A0A0A] p-1 shadow-lg">
          {[{ value: '', label: 'All' }, { value: 'bot', label: 'Bot Applied' }, { value: 'external', label: 'External' }].map(({ value, label }) => (
            <button key={value} onClick={() => { setSourceFilter(value); setPage(1) }} className={`rounded-lg px-4 py-2 text-[10px] font-black uppercase tracking-[0.15em] transition-all ${sourceFilter === value ? value === 'external' ? 'bg-purple-500/20 text-purple-400' : 'bg-amber-500/20 text-amber-500' : 'text-white/30 hover:bg-white/5 hover:text-white/60'}`}>{label}</button>
          ))}
        </div>
        <div className="flex flex-1 gap-3">
          {[{ val: statusFilter, set: setStatusFilter, label: 'All Statuses', opts: STATUSES }, { val: responseFilter, set: setResponseFilter, label: 'All Responses', opts: RESPONSES }, { val: platformFilter, set: setPlatformFilter, label: 'All Platforms', opts: ['', 'stepstone', 'xing', 'linkedin', 'indeed'] }].map((f, i) => (
            <div key={i} className="relative flex-1">
              <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/20" />
              <select value={f.val} onChange={(e) => { f.set(e.target.value); setPage(1) }} className="w-full appearance-none rounded-xl border border-white/10 bg-[#0A0A0A] pl-10 pr-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-white/60 transition-colors focus:border-amber-500/50 focus:outline-none">
                <option value="">{f.label}</option>
                {f.opts.filter(Boolean).map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#0A0A0A] shadow-2xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead><tr className="border-b border-white/10 bg-white/[0.02]">{['Title', 'Company', 'Platform', 'Status', 'Response', 'Date', ''].map((h) => <th key={h} className="whitespace-nowrap px-6 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-white/40">{h}</th>)}</tr></thead>
            <tbody className="font-sans text-sm">
              {loading ? Array.from({ length: 10 }).map((_, i) => <tr key={i} className="border-b border-white/5">{Array.from({ length: 7 }).map((_, j) => <td key={j} className="px-6 py-4"><div className="h-4 w-full rounded bg-white/5 shimmer"></div></td>)}</tr>) : apps.length === 0 ? (
                <tr><td colSpan={7} className="px-6 py-16 text-center"><div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-white/5"><Send className="h-6 w-6 text-white/20" /></div><p className="text-sm font-black uppercase tracking-[0.2em] text-white/40">No applications found</p></td></tr>
              ) : apps.map((a) => (
                <tr key={a.id} className="group border-b border-white/5 transition-colors hover:bg-white/[0.02]">
                  <td className="max-w-[250px] px-6 py-4"><div className="truncate font-bold text-white/80 group-hover:text-white transition-colors">{a.job_title || '-'}</div></td>
                  <td className="px-6 py-4"><div className="text-white/40">{a.company || '-'}</div></td>
                  <td className="px-6 py-4"><span className={`inline-flex rounded-lg border px-2.5 py-1 text-[9px] font-black uppercase tracking-wider ${a.platform === 'stepstone' ? 'border-amber-500/20 bg-amber-500/10 text-amber-500' : a.platform === 'xing' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400' : a.platform === 'linkedin' ? 'border-blue-500/20 bg-blue-500/10 text-blue-400' : a.platform === 'indeed' ? 'border-purple-500/20 bg-purple-500/10 text-purple-400' : 'border-white/10 bg-white/5 text-white/30'}`}>{a.platform}</span></td>
                  <td className="px-6 py-4"><span className={`inline-flex rounded-lg border px-2.5 py-1 text-[9px] font-black uppercase tracking-wider ${a.status === 'success' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400' : a.status === 'failed' ? 'border-red-500/20 bg-red-500/10 text-red-400' : a.status === 'pending' ? 'border-amber-500/20 bg-amber-500/10 text-amber-500' : a.status === 'external' ? 'border-purple-500/20 bg-purple-500/10 text-purple-400' : 'border-white/10 bg-white/5 text-white/30'}`}>{a.status}</span></td>
                  <td className="px-6 py-4"><select value={a.response_status || 'waiting'} onChange={(e) => updateResponse(a.id, e.target.value)} className="cursor-pointer appearance-none rounded-lg border border-white/10 bg-black/50 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-white/60 transition-colors hover:border-white/20 focus:border-amber-500/50 focus:outline-none">{RESPONSES.filter(Boolean).map((r) => <option key={r} value={r}>{r}</option>)}</select></td>
                  <td className="whitespace-nowrap px-6 py-4 text-[11px] font-mono text-white/30">{a.applied_at?.split('T')[0] || '-'}</td>
                  <td className="px-6 py-4 text-right">{a.url && <a href={a.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center rounded-lg p-2 text-white/20 transition-colors hover:bg-white/5 hover:text-amber-500" title="Open Job Posting"><ExternalLink className="h-4 w-4" /></a>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {total > 25 && (
          <div className="flex items-center justify-between border-t border-white/10 bg-white/[0.02] px-6 py-4">
            <span className="text-[10px] font-bold uppercase tracking-wider text-white/40">Showing {(page - 1) * 25 + 1} to {Math.min(page * 25, total)} of {total}</span>
            <div className="flex gap-2">
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="flex items-center justify-center rounded-lg border border-white/10 bg-[#0A0A0A] p-2 text-white/60 transition-colors hover:bg-white/5 hover:text-white disabled:opacity-30"><ChevronLeft className="h-4 w-4" /></button>
              <button onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(total / 25)} className="flex items-center justify-center rounded-lg border border-white/10 bg-[#0A0A0A] p-2 text-white/60 transition-colors hover:bg-white/5 hover:text-white disabled:opacity-30"><ChevronRight className="h-4 w-4" /></button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
