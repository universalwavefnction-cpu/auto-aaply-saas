import { useState, useEffect, useRef } from 'react'
import { Bot, Play, Square, Terminal, Activity, CheckCircle2, XCircle, AlertCircle, Camera, MousePointer2, Send } from 'lucide-react'
import { api } from '../api'

interface LogEntry { type: string; level?: string; category?: string; event?: string; message?: string; data?: any; ts?: string }

export default function BotLive() {
  const [running, setRunning] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [stats, setStats] = useState({ applied: 0, failed: 0, skipped: 0, total: 0, fields_filled: 0, fields_total: 0 })
  const [screenshotUrl, setScreenshotUrl] = useState('')
  const [status, setStatus] = useState('idle')
  const logRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    api.getBotStatus().then(async (res) => {
      if (res.running) {
        setRunning(true); setStatus('running'); if (res.stats) setStats(res.stats)
        // Restore logs from current session
        if (res.session_id) {
          try {
            const logsRes = await api.getBotLogs(res.session_id)
            const past = (logsRes.logs || logsRes || []).map((l: any) => ({ type: 'log', level: l.level, category: l.category, event: l.event, message: l.data?.message || l.event, ts: l.timestamp }))
            setLogs(past.slice(-500))
          } catch {}
        }
        connectSSE()
      }
    })
    return () => { eventSourceRef.current?.close() }
  }, [])

  useEffect(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight }, [logs])

  const connectSSE = async () => {
    const { token: sseToken } = await api.getStreamToken()
    const es = new EventSource(`/api/bot/stream?token=${sseToken}`)
    eventSourceRef.current = es
    const handleEvent = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'log') setLogs((prev) => [...prev.slice(-500), data])
        else if (data.type === 'progress') setStats(data.data)
        else if (data.type === 'screenshot') setScreenshotUrl(data.url)
        else if (data.type === 'status') { setStatus(data.data); if (data.data === 'complete' || data.data === 'error') setRunning(false) }
      } catch {}
    }
    es.addEventListener('log', handleEvent); es.addEventListener('progress', handleEvent); es.addEventListener('screenshot', handleEvent); es.addEventListener('status', handleEvent); es.addEventListener('ping', () => {})
    es.addEventListener('done', () => { setRunning(false); setStatus('complete'); es.close() })
    es.onerror = () => { es.close(); setRunning((r) => { if (r) { setTimeout(connectSSE, 3000) } return r }) }
  }

  const startBot = async (mode: string) => { setLogs([]); setStats({ applied: 0, failed: 0, skipped: 0, total: 0, fields_filled: 0, fields_total: 0 }); setScreenshotUrl(''); setStatus('starting'); setRunning(true); await api.startBot(mode); setTimeout(connectSSE, 500) }
  const stopBot = async () => {
    try { await api.stopBot() } catch {}
    setStatus('stopping')
    // If SSE 'done' event doesn't arrive within 5s, force UI to stopped state
    setTimeout(() => { setRunning((r) => { if (r) { setStatus('idle'); return false } return r }) }, 5000)
  }

  const levelColor = (level?: string) => { switch (level) { case 'error': return 'text-red-400 bg-red-500/10 border-red-500/20'; case 'warn': return 'text-amber-400 bg-amber-500/10 border-amber-500/20'; case 'info': return 'text-white/80 bg-white/5 border-white/10'; default: return 'text-white/40 bg-transparent border-transparent' } }
  const eventIcon = (event?: string) => { switch (event) { case 'success': return <CheckCircle2 className="h-3 w-3 text-emerald-500" />; case 'error': case 'crash': return <XCircle className="h-3 w-3 text-red-500" />; case 'field_filled': return <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />; case 'field_skipped': return <div className="h-1.5 w-1.5 rounded-full border border-white/40" />; case 'screenshot': return <Camera className="h-3 w-3 text-blue-400" />; case 'button_found': return <MousePointer2 className="h-3 w-3 text-purple-400" />; case 'clicking_apply': return <Activity className="h-3 w-3 text-amber-500" />; case 'submitting': return <Send className="h-3 w-3 text-emerald-400" />; default: return <div className="h-1 w-1 rounded-full bg-white/20" /> } }

  const progress = stats.total > 0 ? ((stats.applied + stats.failed + stats.skipped) / stats.total) * 100 : 0

  return (
    <div className="flex h-full flex-col space-y-4 sm:space-y-6 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto">
      <div className="flex shrink-0 items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20"><Bot className="h-5 w-5 text-amber-500" /></div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Live Operations</h1>
            <div className="flex items-center gap-2">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">Agent Status</p>
              {running && <div className="flex items-center gap-1.5 rounded-md border border-amber-500/20 bg-amber-500/5 px-2 py-0.5"><div className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.8)]"></div><span className="text-[7px] font-bold uppercase tracking-widest text-amber-500">{status}</span></div>}
              {!running && status === 'complete' && <div className="flex items-center gap-1.5 rounded-md border border-emerald-500/20 bg-emerald-500/5 px-2 py-0.5"><div className="h-1.5 w-1.5 rounded-full bg-emerald-500"></div><span className="text-[7px] font-bold uppercase tracking-widest text-emerald-500">Complete</span></div>}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {!running ? (<>
            <button onClick={() => startBot('scrape_and_apply')} className="group relative flex items-center justify-center gap-2 overflow-hidden rounded-xl bg-amber-500 px-6 py-3 text-[10px] font-black uppercase tracking-wider text-black shadow-[0_0_20px_rgba(245,158,11,0.2)] transition-all hover:scale-[1.02] hover:bg-amber-400 active:scale-[0.98]"><Play className="h-4 w-4" fill="currentColor" />Start Full Cycle</button>
            <button onClick={() => startBot('scrape')} className="rounded-xl border border-white/10 bg-[#0A0A0A] px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-white/60 transition-all hover:bg-white/5 hover:text-white">Scrape Only</button>
            <button onClick={() => startBot('apply')} className="rounded-xl border border-white/10 bg-[#0A0A0A] px-5 py-3 text-[10px] font-bold uppercase tracking-wider text-white/60 transition-all hover:bg-white/5 hover:text-white">Apply Only</button>
          </>) : (
            <button onClick={stopBot} className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-6 py-3 text-[10px] font-black uppercase tracking-wider text-red-400 transition-all hover:bg-red-500/20"><Square className="h-4 w-4" fill="currentColor" />Stop Agent</button>
          )}
        </div>
      </div>

      {stats.total > 0 && (
        <div className="shrink-0 rounded-2xl border border-white/10 bg-[#0A0A0A] p-6 shadow-2xl">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2"><Activity className="h-4 w-4 text-white/40" /><span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">Execution Progress</span></div>
            <div className="flex gap-6 text-[11px] font-bold uppercase tracking-wider">
              <span className="flex items-center gap-2 text-emerald-400"><CheckCircle2 className="h-3 w-3" /> {stats.applied} applied</span>
              <span className="flex items-center gap-2 text-red-400"><XCircle className="h-3 w-3" /> {stats.failed} failed</span>
              <span className="flex items-center gap-2 text-white/40"><AlertCircle className="h-3 w-3" /> {stats.skipped} skipped</span>
              <span className="flex items-center gap-2 text-white/60 tabular-nums">{stats.applied + stats.failed + stats.skipped} / {stats.total}</span>
            </div>
          </div>
          <div className="relative h-3 w-full overflow-hidden rounded-full bg-white/5">
            <div className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-amber-500 to-amber-300 shadow-[0_0_10px_rgba(245,158,11,0.5)] transition-all duration-500 ease-out" style={{ width: `${progress}%` }} />
          </div>
          {stats.fields_total > 0 && (
            <div className="mt-4 flex items-center justify-between border-t border-white/5 pt-4">
              <span className="text-[10px] font-bold uppercase tracking-wider text-white/40">Form Completion Rate</span>
              <div className="flex items-center gap-3">
                <div className="h-1.5 w-32 overflow-hidden rounded-full bg-white/5"><div className="h-full rounded-full bg-blue-500 transition-all duration-500" style={{ width: `${(stats.fields_filled / stats.fields_total) * 100}%` }} /></div>
                <span className="text-[11px] font-black tabular-nums text-blue-400">{Math.round((stats.fields_filled / stats.fields_total) * 100)}%</span>
                <span className="text-[9px] text-white/20">({stats.fields_filled}/{stats.fields_total} fields)</span>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="terminal-bg flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#0A0A0A] shadow-2xl">
        <div className="terminal-header flex shrink-0 items-center justify-between border-b border-white/5 px-6 py-4">
          <div className="flex items-center gap-3"><Terminal className="h-4 w-4 text-white/40" /><span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/60">Terminal Output</span></div>
          <span className="rounded-lg bg-white/5 px-3 py-1 text-[10px] font-bold text-white/40">{logs.length} events</span>
        </div>
        <div ref={logRef} className="custom-scrollbar flex-1 space-y-2 overflow-auto p-6 font-mono text-[11px]">
          {logs.map((log, i) => (
            <div key={i} className={`flex items-start gap-3 rounded-lg border px-3 py-2 transition-colors fadeIn ${levelColor(log.level)}`}>
              <span className="mt-0.5 w-16 shrink-0 tabular-nums opacity-50">{log.ts?.split('T')[1]?.slice(0, 8) || ''}</span>
              <span className="mt-1 flex w-4 shrink-0 justify-center opacity-80">{eventIcon(log.event)}</span>
              <span className="break-all leading-relaxed">{log.message || log.event}</span>
            </div>
          ))}
          {logs.length === 0 && !running && <div className="flex h-full flex-col items-center justify-center text-white/20"><Terminal className="mb-4 h-12 w-12 opacity-20" /><p className="text-[11px] font-black uppercase tracking-[0.2em]">System Ready</p><p className="mt-2 text-[10px]">Awaiting launch sequence initiation</p></div>}
          {running && <div className="flex items-center gap-2 px-3 py-2"><div className="h-3 w-2 animate-pulse bg-amber-500" /><span className="text-[10px] text-white/20">Awaiting input...</span></div>}
        </div>
      </div>
    </div>
  )
}
