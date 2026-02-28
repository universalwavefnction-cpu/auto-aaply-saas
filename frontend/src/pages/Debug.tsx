import { useState, useEffect } from 'react'
import {
  Bug,
  Activity,
  AlertTriangle,
  ChevronRight,
  ChevronDown,
  Clock,
  Filter,
  ArrowLeft,
  Terminal,
  BarChart3,
  HelpCircle,
  XCircle,
  User,
  Download,
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
  const [selectedSessionInfo, setSelectedSessionInfo] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [levelFilter, setLevelFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [expandedLogs, setExpandedLogs] = useState<Set<number>>(new Set())

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
    setUnmatched(unmatchedRes.unmatched_fields || unmatchedRes.fields || unmatchedRes || [])
    setLoading(false)
  }

  const openSession = async (sessionId: string) => {
    const info = sessions.find((s: any) => s.session_id === sessionId)
    setSelectedSession(sessionId)
    setSelectedSessionInfo(info)
    setView('detail')
    setLoading(true)
    setExpandedLogs(new Set())
    const res = await api.getBotLogs(sessionId)
    setLogs(res.logs || res || [])
    setLoading(false)
  }

  const toggleLog = (id: number) => {
    setExpandedLogs((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const filteredLogs = logs.filter((log: any) => {
    if (levelFilter && log.level !== levelFilter) return false
    if (categoryFilter && log.category !== categoryFilter) return false
    return true
  })

  const errorLogs = logs.filter((log: any) => log.level === 'error' || log.level === 'warn')

  const exportLogs = () => {
    const text = filteredLogs
      .map((l: any) => `[${l.timestamp || ''}] [${l.level}] [${l.category}] ${l.event} ${l.data ? JSON.stringify(l.data) : ''}`)
      .join('\n')
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `session_${selectedSession?.slice(0, 8)}_logs.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

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
              onClick={() => { setView('sessions'); setSelectedSession(null); setSelectedSessionInfo(null); setLevelFilter(''); setCategoryFilter('') }}
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
              {view === 'detail' && selectedSessionInfo?.user_email
                ? <span className="text-amber-500">{selectedSessionInfo.user_email}</span>
                : 'Bot Logs & Diagnostics'}
            </p>
          </div>
        </div>
        {view === 'detail' && (
          <button
            onClick={exportLogs}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-[#0A0A0A] px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-white/60 transition-colors hover:bg-white/5 hover:text-white"
          >
            <Download className="h-3.5 w-3.5" />
            Export
          </button>
        )}
      </div>

      {view === 'sessions' ? (
        <>
          {/* Analytics */}
          {analytics && (
            <div className="grid gap-4 md:grid-cols-4">
              <StatCard label="Total Sessions" value={analytics.total_sessions || 0} />
              <StatCard label="Successful Applies" value={analytics.total_successful_applies || analytics.total_applies || 0} color="text-emerald-400" />
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
                    <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${s.error_count > 0 ? 'bg-red-500/10' : 'bg-white/5'}`}>
                      {s.error_count > 0 ? <XCircle className="h-4 w-4 text-red-400" /> : <Terminal className="h-4 w-4 text-white/40" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        {s.user_email && (
                          <span className="flex items-center gap-1 rounded-md border border-amber-500/20 bg-amber-500/5 px-2 py-0.5 text-[9px] font-bold text-amber-500">
                            <User className="h-3 w-3" />
                            {s.user_email}
                          </span>
                        )}
                        <span className="text-[10px] font-mono text-white/30">{s.session_id.slice(0, 12)}</span>
                      </div>
                      <p className="mt-1 text-[10px] text-white/30">
                        {s.started_at?.replace('T', ' ').slice(0, 19) || '—'} &middot; {s.log_count || 0} events
                        {s.ended_at && <span> &middot; {Math.round((new Date(s.ended_at).getTime() - new Date(s.started_at).getTime()) / 1000)}s</span>}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {s.applied > 0 && (
                        <span className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[9px] font-black uppercase text-emerald-400">
                          {s.applied} applied
                        </span>
                      )}
                      {s.failed > 0 && (
                        <span className="rounded-lg border border-red-500/20 bg-red-500/10 px-2.5 py-1 text-[9px] font-black uppercase text-red-400">
                          {s.failed} failed
                        </span>
                      )}
                      {s.error_count > 0 && (
                        <span className="rounded-lg border border-red-500/20 bg-red-500/10 px-2.5 py-1 text-[9px] font-black uppercase text-red-400">
                          {s.error_count} errors
                        </span>
                      )}
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
                {unmatched.slice(0, 30).map((f: any, i: number) => (
                  <div key={i} className="flex items-center justify-between px-6 py-3">
                    <div>
                      <p className="text-sm font-bold text-white/60">{f.field_name || f.label || f.name || JSON.stringify(f)}</p>
                      <p className="text-[10px] text-white/30">{f.platform || ''} {f.count ? `· ${f.count}x` : ''}</p>
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
          {/* Session summary */}
          {selectedSessionInfo && (
            <div className="grid gap-4 md:grid-cols-5">
              <StatCard label="Log Events" value={logs.length} />
              <StatCard label="Errors" value={errorLogs.length} color="text-red-400" />
              <StatCard label="Applied" value={selectedSessionInfo.applied || 0} color="text-emerald-400" />
              <StatCard label="Failed" value={selectedSessionInfo.failed || 0} color="text-red-400" />
              <StatCard label="Fields Filled" value={selectedSessionInfo.fields_filled || 0} color="text-amber-500" />
            </div>
          )}

          {/* Error summary — quick view of all errors */}
          {errorLogs.length > 0 && (
            <div className="rounded-2xl border border-red-500/20 bg-red-500/5 overflow-hidden">
              <div className="flex items-center gap-3 border-b border-red-500/20 px-6 py-3">
                <XCircle className="h-4 w-4 text-red-400" />
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-red-400">
                  Errors & Warnings ({errorLogs.length})
                </span>
              </div>
              <div className="divide-y divide-red-500/10 max-h-64 overflow-auto">
                {errorLogs.map((log: any, i: number) => (
                  <div key={log.id || i} className="px-6 py-3">
                    <div className="flex items-start gap-3">
                      <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[8px] font-black uppercase ${log.level === 'error' ? 'border-red-500/30 bg-red-500/20 text-red-400' : 'border-amber-500/30 bg-amber-500/20 text-amber-400'}`}>
                        {log.level}
                      </span>
                      <span className="text-[10px] font-bold uppercase text-white/30">[{log.category}]</span>
                      <span className="text-xs font-bold text-white/70">{log.event}</span>
                      <span className="ml-auto shrink-0 text-[10px] text-white/20">{(log.timestamp || '').split('T')[1]?.slice(0, 8)}</span>
                    </div>
                    {log.data && (
                      <p className="mt-1 pl-16 text-[11px] text-red-300/70 font-mono break-all">
                        {typeof log.data === 'string' ? log.data : (log.data.message || log.data.error || JSON.stringify(log.data))}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

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
            <button
              onClick={() => setLevelFilter(levelFilter === 'error' ? '' : 'error')}
              className={`flex items-center gap-2 rounded-xl border px-4 text-[10px] font-bold uppercase tracking-wider transition-colors ${levelFilter === 'error' ? 'border-red-500/30 bg-red-500/10 text-red-400' : 'border-white/10 bg-[#0A0A0A] text-white/40 hover:text-red-400'}`}
            >
              <XCircle className="h-3.5 w-3.5" />
              Errors Only
            </button>
            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-[#0A0A0A] px-4">
              <BarChart3 className="h-4 w-4 text-white/20" />
              <span className="text-[10px] font-bold text-white/40">{filteredLogs.length} events</span>
            </div>
          </div>

          {/* Full log entries */}
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
                {filteredLogs.map((log: any, i: number) => {
                  const logId = log.id || i
                  const isExpanded = expandedLogs.has(logId)
                  const hasData = log.data && (typeof log.data === 'object' ? Object.keys(log.data).length > 0 : true)

                  return (
                    <div key={logId}>
                      <div
                        onClick={() => hasData && toggleLog(logId)}
                        className={`flex items-start gap-3 px-4 py-3 transition-colors ${hasData ? 'cursor-pointer hover:bg-white/[0.03]' : ''} ${log.level === 'error' ? 'bg-red-500/[0.03]' : ''}`}
                      >
                        <span className="shrink-0 pt-0.5 text-[10px] text-white/20 tabular-nums">
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
                        <span className="text-white/60 flex-1">{log.event}</span>
                        {log.data?.message && (
                          <span className={`ml-2 truncate max-w-[400px] text-[10px] ${log.level === 'error' ? 'text-red-400/60' : 'text-white/20'}`}>
                            {log.data.message}
                          </span>
                        )}
                        {hasData && (
                          <span className="shrink-0 text-white/20">
                            {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                          </span>
                        )}
                      </div>
                      {isExpanded && hasData && (
                        <div className="border-t border-white/5 bg-white/[0.02] px-4 py-3 ml-8">
                          <pre className="whitespace-pre-wrap break-all text-[10px] text-white/50 max-h-64 overflow-auto">
                            {typeof log.data === 'string' ? log.data : JSON.stringify(log.data, null, 2)}
                          </pre>
                          {log.platform && <p className="mt-2 text-[9px] text-white/20">Platform: {log.platform}</p>}
                          {log.job_id && <p className="text-[9px] text-white/20">Job ID: {log.job_id}</p>}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
