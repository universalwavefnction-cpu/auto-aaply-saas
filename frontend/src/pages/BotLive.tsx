import { useState, useEffect, useRef } from 'react'
import { api } from '../api'

interface LogEntry {
  type: string
  level?: string
  category?: string
  event?: string
  message?: string
  data?: any
  ts?: string
}

export default function BotLive() {
  const [running, setRunning] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [stats, setStats] = useState({
    applied: 0,
    failed: 0,
    skipped: 0,
    total: 0,
    fields_filled: 0,
    fields_total: 0,
  })
  const [screenshotUrl, setScreenshotUrl] = useState('')
  const [status, setStatus] = useState('idle')
  const logRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    api.getBotStatus().then((res) => {
      if (res.running) {
        setRunning(true)
        setStatus('running')
        if (res.stats) setStats(res.stats)
        connectSSE()
      }
    })
    return () => {
      eventSourceRef.current?.close()
    }
  }, [])

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [logs])

  const connectSSE = () => {
    const token = localStorage.getItem('token')
    const es = new EventSource(`/api/bot/stream?token=${token}`)
    eventSourceRef.current = es

    const handleEvent = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'log') {
          setLogs((prev) => [...prev.slice(-500), data])
        } else if (data.type === 'progress') {
          setStats(data.data)
        } else if (data.type === 'screenshot') {
          setScreenshotUrl(data.url)
        } else if (data.type === 'status') {
          setStatus(data.data)
          if (data.data === 'complete' || data.data === 'error') {
            setRunning(false)
          }
        }
      } catch {}
    }

    es.addEventListener('log', handleEvent)
    es.addEventListener('progress', handleEvent)
    es.addEventListener('screenshot', handleEvent)
    es.addEventListener('status', handleEvent)
    es.addEventListener('ping', () => {})
    es.addEventListener('done', () => {
      setRunning(false)
      setStatus('complete')
      es.close()
    })
    es.onerror = () => {
      // Reconnect after brief delay
      setTimeout(() => {
        if (running) connectSSE()
      }, 3000)
    }
  }

  const startBot = async (mode: string) => {
    setLogs([])
    setStats({ applied: 0, failed: 0, skipped: 0, total: 0, fields_filled: 0, fields_total: 0 })
    setScreenshotUrl('')
    setStatus('starting')
    setRunning(true)
    await api.startBot(mode)
    // Small delay then connect SSE
    setTimeout(connectSSE, 500)
  }

  const stopBot = async () => {
    await api.stopBot()
    setStatus('stopping')
  }

  const levelColor = (level?: string) => {
    switch (level) {
      case 'error':
        return 'text-red-400'
      case 'warn':
        return 'text-amber-400'
      case 'info':
        return 'text-white/60'
      default:
        return 'text-white/30'
    }
  }

  const eventIcon = (event?: string) => {
    switch (event) {
      case 'success':
        return '✓'
      case 'error':
      case 'crash':
        return '✗'
      case 'field_filled':
        return '●'
      case 'field_skipped':
        return '○'
      case 'screenshot':
        return '📸'
      case 'button_found':
        return '→'
      case 'clicking_apply':
        return '⚡'
      case 'submitting':
        return '↑'
      default:
        return '›'
    }
  }

  const progress =
    stats.total > 0 ? ((stats.applied + stats.failed + stats.skipped) / stats.total) * 100 : 0

  return (
    <div className="flex h-full flex-col space-y-4 p-8">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-amber-500/10 p-1.5">
            <svg
              className="h-4 w-4 text-amber-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M13 10V3L4 14h7v7l9-11h-7z" strokeLinecap="round" strokeWidth="2.5" />
            </svg>
          </div>
          <span className="text-[11px] font-black uppercase tracking-[0.2em] text-white/60">
            Live Bot
          </span>
          {running && (
            <div className="flex items-center gap-1.5 rounded-md border border-amber-500/20 bg-amber-500/5 px-2 py-0.5">
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500"></div>
              <span className="text-[7px] font-bold uppercase tracking-widest text-amber-500">
                {status}
              </span>
            </div>
          )}
          {!running && status === 'complete' && (
            <div className="flex items-center gap-1.5 rounded-md border border-[#27C93F]/20 bg-[#27C93F]/5 px-2 py-0.5">
              <div className="h-1.5 w-1.5 rounded-full bg-[#27C93F]"></div>
              <span className="text-[7px] font-bold uppercase tracking-widest text-[#27C93F]">
                Complete
              </span>
            </div>
          )}
        </div>

        <div className="flex gap-2">
          {!running ? (
            <>
              <button
                onClick={() => startBot('scrape_and_apply')}
                className="rounded-xl bg-amber-500 px-5 py-2.5 text-[10px] font-black uppercase tracking-wider text-white shadow-lg shadow-amber-500/20 transition-all hover:bg-amber-600"
              >
                Start Full Cycle
              </button>
              <button
                onClick={() => startBot('scrape')}
                className="rounded-xl border border-white/5 bg-white/5 px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-white/40 transition-colors hover:text-amber-500"
              >
                Scrape Only
              </button>
              <button
                onClick={() => startBot('apply')}
                className="rounded-xl border border-white/5 bg-white/5 px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-white/40 transition-colors hover:text-amber-500"
              >
                Apply Only
              </button>
            </>
          ) : (
            <button
              onClick={stopBot}
              className="rounded-xl border border-red-500/20 bg-red-500/10 px-5 py-2.5 text-[10px] font-black uppercase tracking-wider text-red-400 transition-all hover:bg-red-500/20"
            >
              Stop Bot
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      {stats.total > 0 && (
        <div className="shrink-0 rounded-xl border border-white/5 bg-[#0A0A0A] p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[8px] font-black uppercase tracking-[0.2em] text-white/15">
              Progress
            </span>
            <div className="flex gap-4 text-[10px] font-bold">
              <span className="text-[#27C93F]">{stats.applied} applied</span>
              <span className="text-red-400">{stats.failed} failed</span>
              <span className="text-white/30">{stats.skipped} skipped</span>
              <span className="text-white/20">
                {stats.applied + stats.failed + stats.skipped}/{stats.total}
              </span>
            </div>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
            <div
              className="h-full rounded-full bg-amber-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          {stats.fields_total > 0 && (
            <div className="mt-2 text-[9px] text-white/20">
              Form fill rate:{' '}
              <span className="font-bold text-amber-500">
                {Math.round((stats.fields_filled / stats.fields_total) * 100)}%
              </span>{' '}
              ({stats.fields_filled}/{stats.fields_total} fields)
            </div>
          )}
        </div>
      )}

      {/* Activity Log — Full Width */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-white/5 bg-[#0A0A0A]">
        <div className="flex shrink-0 items-center justify-between border-b border-white/5 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span className="font-black text-amber-500">_</span>
            <span className="text-[8px] font-black uppercase tracking-[0.2em] text-white/15">
              Activity Log
            </span>
          </div>
          <span className="text-[8px] font-bold text-white/10">{logs.length} events</span>
        </div>
        <div
          ref={logRef}
          className="custom-scrollbar flex-1 space-y-0.5 overflow-auto p-3 font-mono text-[11px]"
        >
          {logs.map((log, i) => (
            <div
              key={i}
              className={`flex gap-2 rounded px-1 py-0.5 hover:bg-white/[0.02] ${levelColor(log.level)}`}
            >
              <span className="w-16 shrink-0 tabular-nums text-white/10">
                {log.ts?.split('T')[1]?.slice(0, 8) || ''}
              </span>
              <span className="w-4 shrink-0 text-center">{eventIcon(log.event)}</span>
              <span className="break-all">{log.message || log.event}</span>
            </div>
          ))}
          {logs.length === 0 && !running && (
            <div className="py-10 text-center text-white/10">
              <p className="text-[11px] font-black uppercase tracking-[0.2em]">Ready</p>
              <p className="mt-1 text-[10px]">Click "Start Full Cycle" to begin</p>
            </div>
          )}
          {running && (
            <div className="animate-pulse px-1 text-lg font-bold tracking-widest text-amber-500">
              _
            </div>
          )}
        </div>
      </div>

      <style>{`.custom-scrollbar::-webkit-scrollbar{width:4px}.custom-scrollbar::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.05);border-radius:10px}`}</style>
    </div>
  )
}
