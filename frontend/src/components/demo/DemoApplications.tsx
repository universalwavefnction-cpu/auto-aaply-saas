import { useState, useEffect } from 'react'
import { Send, Search, CheckCircle2, XCircle, Clock } from 'lucide-react'
import { DEMO_APPLICATIONS } from './demoData'

export default function DemoApplications() {
  const [visibleRows, setVisibleRows] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setVisibleRows((v) => {
        if (v >= DEMO_APPLICATIONS.length) {
          clearInterval(timer)
          return v
        }
        return v + 1
      })
    }, 200)
    return () => clearInterval(timer)
  }, [])

  const statusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-400" />
      default:
        return <Clock className="h-4 w-4 text-amber-500" />
    }
  }

  const statusBadge = (status: string) => {
    const styles: Record<string, string> = {
      success: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400',
      failed: 'border-red-500/20 bg-red-500/10 text-red-400',
      pending: 'border-amber-500/20 bg-amber-500/10 text-amber-500',
    }
    return styles[status] || styles.pending
  }

  return (
    <div className="space-y-6 sm:space-y-8 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="shrink-0 rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
            <Send className="h-5 w-5 text-amber-500" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white truncate">
              Applications
            </h1>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
              {DEMO_APPLICATIONS.length} Total Submissions
            </p>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-[#0A0A0A] px-4 py-3">
        <Search className="h-4 w-4 text-white/30 shrink-0" />
        <span className="text-sm text-white/30">Search applications...</span>
        <div className="ml-auto flex gap-2">
          {['All', 'Success', 'Pending', 'Failed'].map((f, i) => (
            <span
              key={f}
              className={`rounded-lg px-3 py-1 text-[9px] font-bold uppercase tracking-wider ${
                i === 0
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                  : 'text-white/30 border border-transparent'
              }`}
            >
              {f}
            </span>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="demo-hotspot rounded-2xl border border-white/5 bg-[#0A0A0A] overflow-hidden">
        {/* Table Header */}
        <div className="hidden sm:grid grid-cols-12 gap-4 border-b border-white/5 px-6 py-3">
          <span className="col-span-1 text-[9px] font-black uppercase tracking-wider text-white/30">
            Status
          </span>
          <span className="col-span-4 text-[9px] font-black uppercase tracking-wider text-white/30">
            Position
          </span>
          <span className="col-span-3 text-[9px] font-black uppercase tracking-wider text-white/30">
            Company
          </span>
          <span className="col-span-2 text-[9px] font-black uppercase tracking-wider text-white/30">
            Platform
          </span>
          <span className="col-span-2 text-[9px] font-black uppercase tracking-wider text-white/30">
            Date
          </span>
        </div>

        {/* Table Rows */}
        <div className="divide-y divide-white/5">
          {DEMO_APPLICATIONS.slice(0, visibleRows).map((app, i) => (
            <div
              key={app.id}
              className="grid grid-cols-1 sm:grid-cols-12 gap-2 sm:gap-4 px-6 py-4 transition-colors hover:bg-white/[0.02] fadeIn"
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <div className="sm:col-span-1 flex items-center gap-2 sm:gap-0">
                {statusIcon(app.status)}
                <span className="sm:hidden text-xs font-bold text-white/60">{app.title}</span>
              </div>
              <div className="hidden sm:flex sm:col-span-4 items-center">
                <span className="text-sm font-bold text-white/80 truncate">{app.title}</span>
              </div>
              <div className="sm:col-span-3 flex items-center">
                <span className="text-sm text-white/50 truncate">{app.company}</span>
              </div>
              <div className="sm:col-span-2 flex items-center">
                <span className="rounded-lg bg-white/5 px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider text-white/30">
                  {app.platform}
                </span>
              </div>
              <div className="sm:col-span-2 flex items-center justify-between">
                <span className="text-[11px] tabular-nums text-white/30">{app.date}</span>
                <span
                  className={`rounded-md border px-2 py-0.5 text-[9px] font-black uppercase tracking-wider ${statusBadge(app.status)}`}
                >
                  {app.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
