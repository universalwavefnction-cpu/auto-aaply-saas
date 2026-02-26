import { useState, useEffect } from 'react'
import { api } from '../api'

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)

  useEffect(() => {
    api.getStats().then(setStats)
  }, [])

  if (!stats) return (
    <div className="flex items-center justify-center h-full">
      <div className="text-white/20 text-[11px] font-bold uppercase tracking-[0.2em] animate-pulse">Initializing Mission Control...</div>
    </div>
  )

  const statCards = [
    { label: 'Live Applications', val: stats.total_applications.toLocaleString(), accent: 'text-amber-500' },
    { label: 'Success Rate', val: `${stats.success_rate}%`, accent: 'text-[#27C93F]' },
    { label: 'Jobs Discovered', val: stats.total_jobs_discovered.toLocaleString(), accent: 'text-white' },
    { label: 'Responses', val: Object.entries(stats.by_response || {}).filter(([k]) => k !== 'waiting' && k !== 'PENDING').reduce((s: number, [, v]) => s + (v as number), 0).toString(), accent: 'text-blue-400' },
  ]

  const platformData = Object.entries(stats.by_platform || {}) as [string, number][]
  const statusData = Object.entries(stats.by_status || {}) as [string, number][]

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-amber-500/10 rounded-md">
            <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" strokeLinecap="round" strokeWidth="2.5"/>
            </svg>
          </div>
          <span className="uppercase font-black tracking-[0.2em] text-[11px] text-white/60">Mission Control</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-[#27C93F]/20 bg-[#27C93F]/5">
          <div className="w-1.5 h-1.5 rounded-full bg-[#27C93F] animate-pulse"></div>
          <span className="text-[8px] font-bold text-[#27C93F] uppercase tracking-widest">Active</span>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-6">
        {statCards.map((stat, i) => (
          <div key={i} className="bg-[#0A0A0A] border border-white/5 p-5 rounded-xl space-y-2 hover:border-white/10 transition-colors">
            <span className="text-white/20 uppercase font-black text-[8px] tracking-[0.2em]">{stat.label}</span>
            <p className={`text-3xl font-black tracking-tighter ${stat.accent}`}>{stat.val}</p>
          </div>
        ))}
      </div>

      {/* Platform + Status breakdown */}
      <div className="grid grid-cols-2 gap-6">
        {/* By Platform */}
        <div className="bg-[#0A0A0A] border border-white/5 rounded-xl p-6">
          <span className="text-white/20 uppercase font-black text-[8px] tracking-[0.2em] block mb-4">By Platform</span>
          <div className="space-y-3">
            {platformData.map(([name, count]) => {
              const max = Math.max(...platformData.map(([, v]) => v))
              const pct = (count / max) * 100
              const colors: Record<string, string> = {
                stepstone: 'bg-amber-500', xing: 'bg-emerald-500', linkedin: 'bg-blue-500', testplatform: 'bg-white/20'
              }
              return (
                <div key={name} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-white/40 uppercase tracking-wider">{name}</span>
                    <span className="text-[10px] font-black text-white/60">{count.toLocaleString()}</span>
                  </div>
                  <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${colors[name] || 'bg-white/20'}`} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* By Status */}
        <div className="bg-[#0A0A0A] border border-white/5 rounded-xl p-6">
          <span className="text-white/20 uppercase font-black text-[8px] tracking-[0.2em] block mb-4">By Status</span>
          <div className="space-y-3">
            {statusData.map(([name, count]) => {
              const max = Math.max(...statusData.map(([, v]) => v))
              const pct = (count / max) * 100
              const colors: Record<string, string> = {
                success: 'bg-[#27C93F]', failed: 'bg-red-500', pending: 'bg-amber-500', skipped: 'bg-white/20'
              }
              return (
                <div key={name} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-white/40 uppercase tracking-wider">{name}</span>
                    <span className="text-[10px] font-black text-white/60">{count.toLocaleString()}</span>
                  </div>
                  <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${colors[name] || 'bg-white/20'}`} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Recent Applications - Audit Log Style */}
      <div className="bg-[#0A0A0A] border border-white/5 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="text-amber-500 font-black">_</span>
            <span className="uppercase font-black tracking-[0.2em] text-[9px] text-white/40">Recent Activity</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-amber-500/10">
            <div className="w-1 h-1 rounded-full bg-amber-500 animate-pulse"></div>
            <span className="text-[7px] text-amber-500 font-black uppercase">Live</span>
          </div>
        </div>
        <div className="font-mono text-[12px] space-y-2">
          {(stats.recent || []).map((a: any) => {
            const statusColors: Record<string, string> = {
              success: 'text-[#27C93F]', failed: 'text-red-400', pending: 'text-amber-500', applying: 'text-blue-400'
            }
            return (
              <div key={a.id} className="flex gap-6 group hover:bg-white/[0.02] px-2 py-1.5 rounded-lg transition-colors">
                <span className="text-white/15 w-20 shrink-0 tabular-nums">{a.applied_at?.split('T')[1]?.slice(0, 8) || '--:--:--'}</span>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-black border h-fit mt-0.5 uppercase tracking-wider shrink-0 min-w-[60px] text-center ${
                  a.status === 'success' ? 'bg-[#27C93F]/10 text-[#27C93F] border-[#27C93F]/20' :
                  a.status === 'failed' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                  'bg-amber-500/10 text-amber-500 border-amber-500/20'
                }`}>
                  {a.status}
                </span>
                <span className="text-white/50 tracking-tight group-hover:text-white/80 transition-colors truncate">
                  {a.job_title || 'Unknown Position'}
                </span>
                <span className="text-white/20 ml-auto shrink-0">{a.company || ''}</span>
                <span className="text-[9px] text-white/10 uppercase font-bold shrink-0">{a.platform}</span>
              </div>
            )
          })}
          <div className="mt-2 text-white/20 animate-pulse font-bold tracking-widest text-lg px-2">_</div>
        </div>
      </div>
    </div>
  )
}
