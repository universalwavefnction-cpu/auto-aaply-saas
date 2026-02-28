import { useState, useEffect } from 'react'
import {
  Bug,
  Activity,
  AlertTriangle,
  ChevronRight,
  Clock,
  Filter,
  ArrowLeft,
  Terminal,
  BarChart3,
  HelpCircle,
} from 'lucide-react'
import { api } from '../api'

const LEVEL_COLORS: Record<string, string> = {
  debug: 'text-white/30',
  info: 'text-blue-400',
  warn: 'text-amber-500',
  error: 'text-red-400',
}

const LEVEL_BG: Record<string, string> = {
  debug: 'border-white/10 bg-white/5',
  info: 'border-blue-500/20 bg-blue-500/10',
  warn: 'border-amber-500/20 bg-amber-500/10',
  error: 'border-red-500/20 bg-red-500/10',
}

const CATEGORY_COLORS: Record<string, string> = {
  browser: 'text-purple-400',
  form: 'text-emerald-400',
  network: 'text-blue-400',
  apply: 'text-amber-500',
  scrape: 'text-cyan-400',
  system: 'text-white/40',
}

type View = 'sessions' | 'detail'

export default function Debug() {
  const [view, setView] = useState<View>('sessions')
  const [sessions, setSessions] = useState<any[]>([])
  const [logs, setLogs] = useState<any[]>([])
  const [analytics, setAnalytics] = useState<any>(null)
  const [unmatched, setUnmatched] = useState<any[]>([])
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [levelFilter, setLevelFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')

  useEffect(() => {
    loadOverview()
  }, [])

  const loadOverview = async () => {
    setLoading(true)
    const [sessionsRes, analyticsRes, unmatchedRes] = await Promise.all([
      api.getBotSessions(),
      api.getBotAnalytics(),
      api.getUnmatchedFields(),
    ])
    setSessions(sessionsRes.sessions || sessionsRes || [])
    setAnalytics(analyticsRes)
    setUnmatched(unmatchedRes.fields || unmatchedRes || [])
    setLoading(false)
  }

  const openSession = async (sessionId: string) => {
    setSelectedSession(sessionId)
    setView('detail')
    setLoading(true)
    const res = await api.getBotLogs(sessionId)
    setLogs(res.logs || res || [])
    setLoading(false)
  }

  const filteredLogs = logs.filter((log: any) => {
    if (levelFilter && log.level !== levelFilter) return false
    if (categoryFilter && log.category !== categoryFilter) return false
    return true
  })

  const StatCard = ({ label, value, color }: { label: string; value: string | number; color?: string }) => (
    <div className="rounded-xl border border-white/10 bg-[#0A0A0A] p-5">
      <p className="text-[9px] font-black uppercase tracking-[0.2em] text-white/40">{label}</p>
      <p className={`mt-1 text-2xl font-black ${color || 'text-white'}`}>{value}</p>
    </div>
  )

  if (loading && view === 'sessions') {
    return (
      <div className="space-y-6 p-8 max-w-6xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-white/5 shimmer" />
          <div className="space-y-2">
            <div className="h-6 w-40 rounded bg-white/5 shimmer" />
            <div className="h-3 w-24 rounded bg-white/5 shimmer" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-white/5 shimmer" />
          ))}
        </div>
        <div className="h-64 rounded-2xl bg-white/5 shimmer" />
      </div>
    )
  }

  return (
    <div className="space-y-6 p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {view === 'detail' && (
            <button
              onClick={() => { setView('sessions'); setSelectedSession(null) }}
              className="rounded-lg border border-white/10 p-2 text-white/40 transition-colors hover:bg-white/5 hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
          )}
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
            <Bug className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              {view === 'sessions' ? 'Debug Console' : `Session ${selectedSession?.slice(0, 8)}...`}
            </h1>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
              Bot Logs & Diagnostics
            </p>
          </div>
        </div>
      </div>

      {view === 'sessions' ? (
        <>
          {/* Analytics */}
          {analytics && (
            <div className="grid gap-4 md:grid-cols-4">
              <StatCard label="Total Sessions" value={analytics.total_sessions || 0} />
              <StatCard label="Applications Sent" value={analytics.total_applies || 0} color="text-emerald-400" />
              <StatCard label="Failures" value={analytics.total_failures || 0} color="text-red-400" />
              <StatCard label="Fields Filled" value={analytics.total_fields_filled || 0} color="text-amber-500" />
            </div>
          )}

          {/* Sessions list */}
          <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] shadow-2xl overflow-hidden">
            <div className="flex items-center gap-3 border-b border-white/10 bg-white/[0.02] px-6 py-4">
              <Terminal className="h-4 w-4 text-white/40" />
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                Bot Sessions
              </span>
              <span className="ml-auto text-[10px] font-bold text-white/20">{sessions.length} total</span>
            </div>

            {sessions.length === 0 ? (
              <div className="px-6 py-16 text-center">
                <Activity className="mx-auto mb-4 h-8 w-8 text-white/10" />
                <p className="text-sm font-bold text-white/30">No bot sessions yet</p>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {sessions.map((s: any) => (
                  <button
                    key={s.session_id}
                    onClick={() => openSession(s.session_id)}
                    className="flex w-full items-center gap-4 px-6 py-4 text-left transition-colors hover:bg-white/[0.02]"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/5">
                      <Terminal className="h-4 w-4 text-white/40" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold text-white/80 truncate">
                        {s.session_id}
                      </p>
                      <p className="text-[10px] text-white/30">
                        {s.user_email && <span className="text-amber-500/70">{s.user_email} &middot; </span>}
                        {s.started_at || s.timestamp || '—'} &middot; {s.log_count || s.total || 0} events
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {(s.applies || s.total_applies) ? (
                        <span className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[9px] font-black uppercase text-emerald-400">
                          {s.applies || s.total_applies} applied
                        </span>
                      ) : null}
                      {(s.errors || s.total_errors) ? (
                        <span className="rounded-lg border border-red-500/20 bg-red-500/10 px-2.5 py-1 text-[9px] font-black uppercase text-red-400">
                          {s.errors || s.total_errors} errors
                        </span>
                      ) : null}
                      <ChevronRight className="h-4 w-4 text-white/20" />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Unmatched fields */}
          {unmatched.length > 0 && (
            <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] shadow-2xl overflow-hidden">
              <div className="flex items-center gap-3 border-b border-white/10 bg-white/[0.02] px-6 py-4">
                <HelpCircle className="h-4 w-4 text-amber-500" />
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                  Unmatched Form Fields
                </span>
                <span className="ml-auto text-[10px] font-bold text-amber-500">{unmatched.length}</span>
              </div>
              <div className="divide-y divide-white/5">
                {unmatched.slice(0, 20).map((f: any, i: number) => (
                  <div key={i} className="flex items-center justify-between px-6 py-3">
                    <div>
                      <p className="text-sm font-bold text-white/60">{f.field_name || f.label || f.name || JSON.stringify(f)}</p>
                      <p className="text-[10px] text-white/30">{f.platform || ''} &middot; {f.count || 1}x</p>
                    </div>
                    <AlertTriangle className="h-4 w-4 text-amber-500/50" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          {/* Filters */}
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/20" />
              <select
                value={levelFilter}
                onChange={(e) => setLevelFilter(e.target.value)}
                className="w-full appearance-none rounded-xl border border-white/10 bg-[#0A0A0A] pl-10 pr-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-white/60 focus:border-amber-500/50 focus:outline-none"
              >
                <option value="">All Levels</option>
                {['debug', 'info', 'warn', 'error'].map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>
            <div className="relative flex-1">
              <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/20" />
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full appearance-none rounded-xl border border-white/10 bg-[#0A0A0A] pl-10 pr-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-white/60 focus:border-amber-500/50 focus:outline-none"
              >
                <option value="">All Categories</option>
                {['browser', 'form', 'network', 'apply', 'scrape', 'system'].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-[#0A0A0A] px-4">
              <BarChart3 className="h-4 w-4 text-white/20" />
              <span className="text-[10px] font-bold text-white/40">{filteredLogs.length} events</span>
            </div>
          </div>

          {/* Log entries */}
          <div className="rounded-2xl border border-white/10 bg-[#0A0A0A] shadow-2xl overflow-hidden">
            {loading ? (
              <div className="space-y-2 p-6">
                {Array.from({ length: 10 }).map((_, i) => (
                  <div key={i} className="h-10 rounded bg-white/5 shimmer" />
                ))}
              </div>
            ) : filteredLogs.length === 0 ? (
              <div className="px-6 py-16 text-center">
                <Terminal className="mx-auto mb-4 h-8 w-8 text-white/10" />
                <p className="text-sm font-bold text-white/30">No log entries</p>
              </div>
            ) : (
              <div className="divide-y divide-white/5 font-mono text-xs">
                {filteredLogs.map((log: any, i: number) => (
                  <div
                    key={log.id || i}
                    className="flex items-start gap-3 px-4 py-3 hover:bg-white/[0.02] transition-colors"
                  >
                    <span className="shrink-0 pt-0.5 text-[10px] text-white/20">
                      <Clock className="inline h-3 w-3 mr-1" />
                      {(log.timestamp || '').split('T')[1]?.slice(0, 8) || '—'}
                    </span>
                    <span
                      className={`shrink-0 rounded border px-2 py-0.5 text-[9px] font-black uppercase ${LEVEL_BG[log.level] || LEVEL_BG.info}`}
                    >
                      <span className={LEVEL_COLORS[log.level] || 'text-white/40'}>{log.level}</span>
                    </span>
                    <span
                      className={`shrink-0 text-[10px] font-bold uppercase ${CATEGORY_COLORS[log.category] || 'text-white/30'}`}
                    >
                      [{log.category}]
                    </span>
                    <span className="text-white/60">{log.event}</span>
                    {log.data && (
                      <span className="ml-auto truncate max-w-[300px] text-[10px] text-white/20">
                        {typeof log.data === 'string' ? log.data : JSON.stringify(log.data)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
