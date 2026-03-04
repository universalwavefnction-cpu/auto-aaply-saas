import { useState, useEffect, useRef } from 'react'
import {
  Bot,
  Play,
  Terminal,
  Activity,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Send,
  MousePointer2,
  Camera,
} from 'lucide-react'
import { DEMO_BOT_LOGS } from './demoData'

function useCountUp(target: number, duration = 1500, delay = 0) {
  const [value, setValue] = useState(0)
  const ref = useRef<number>(0)

  useEffect(() => {
    const timeout = setTimeout(() => {
      const start = performance.now()
      const animate = (now: number) => {
        const elapsed = now - start
        const progress = Math.min(elapsed / duration, 1)
        const eased = 1 - Math.pow(1 - progress, 3)
        setValue(Math.round(eased * target))
        if (progress < 1) ref.current = requestAnimationFrame(animate)
      }
      ref.current = requestAnimationFrame(animate)
    }, delay)
    return () => {
      clearTimeout(timeout)
      cancelAnimationFrame(ref.current)
    }
  }, [target, duration, delay])

  return value
}

export default function DemoBotLive() {
  const [visibleLines, setVisibleLines] = useState(0)
  const logRef = useRef<HTMLDivElement>(null)

  const applied = useCountUp(12, 3000, 500)
  const failed = useCountUp(2, 3000, 500)
  const skipped = useCountUp(1, 3000, 500)
  const total = 23
  const progress = ((applied + failed + skipped) / total) * 100

  useEffect(() => {
    const timer = setInterval(() => {
      setVisibleLines((v) => {
        if (v >= DEMO_BOT_LOGS.length) {
          clearInterval(timer)
          return v
        }
        return v + 1
      })
    }, 400)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [visibleLines])

  const eventIcon = (event?: string) => {
    switch (event) {
      case 'success':
        return <CheckCircle2 className="h-3 w-3 text-emerald-500" />
      case 'error':
        return <XCircle className="h-3 w-3 text-red-500" />
      case 'field_filled':
        return <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />
      case 'upload':
        return <Camera className="h-3 w-3 text-blue-400" />
      case 'clicking_apply':
        return <MousePointer2 className="h-3 w-3 text-purple-400" />
      case 'submitting':
        return <Send className="h-3 w-3 text-emerald-400" />
      default:
        return <div className="h-1 w-1 rounded-full bg-white/20" />
    }
  }

  const levelColor = (level?: string) => {
    switch (level) {
      case 'error':
        return 'text-red-400 bg-red-500/10 border-red-500/20'
      case 'warn':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20'
      case 'info':
        return 'text-white/80 bg-white/5 border-white/10'
      default:
        return 'text-white/40 bg-transparent border-transparent'
    }
  }

  return (
    <div className="flex h-full flex-col space-y-4 sm:space-y-6 p-4 sm:p-6 md:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex shrink-0 items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-amber-500/10 p-2 border border-amber-500/20">
            <Bot className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Live Operations</h1>
            <div className="flex items-center gap-2">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                Agent Status
              </p>
              <div className="flex items-center gap-1.5 rounded-md border border-amber-500/20 bg-amber-500/5 px-2 py-0.5">
                <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.8)]"></div>
                <span className="text-[7px] font-bold uppercase tracking-widest text-amber-500">
                  running
                </span>
              </div>
            </div>
          </div>
        </div>
        <div className="demo-hotspot flex items-center gap-3">
          <div className="group relative flex items-center justify-center gap-2 overflow-hidden rounded-xl bg-amber-500 px-6 py-3 text-[10px] font-black uppercase tracking-wider text-black shadow-[0_0_20px_rgba(245,158,11,0.2)]">
            <Play className="h-4 w-4" fill="currentColor" />
            Start Full Cycle
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="shrink-0 rounded-2xl border border-white/10 bg-[#0A0A0A] p-6 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-white/40" />
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
              Execution Progress
            </span>
          </div>
          <div className="flex gap-6 text-[11px] font-bold uppercase tracking-wider">
            <span className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="h-3 w-3" /> {applied} applied
            </span>
            <span className="flex items-center gap-2 text-red-400">
              <XCircle className="h-3 w-3" /> {failed} failed
            </span>
            <span className="flex items-center gap-2 text-white/40">
              <AlertCircle className="h-3 w-3" /> {skipped} skipped
            </span>
            <span className="flex items-center gap-2 text-white/60 tabular-nums">
              {applied + failed + skipped} / {total}
            </span>
          </div>
        </div>
        <div className="relative h-3 w-full overflow-hidden rounded-full bg-white/5">
          <div
            className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-amber-500 to-amber-300 shadow-[0_0_10px_rgba(245,158,11,0.5)] transition-all duration-1000 ease-out"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      </div>

      {/* Terminal */}
      <div className="demo-hotspot terminal-bg flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#0A0A0A] shadow-2xl">
        <div className="terminal-header flex shrink-0 items-center justify-between border-b border-white/5 px-6 py-4">
          <div className="flex items-center gap-3">
            <Terminal className="h-4 w-4 text-white/40" />
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/60">
              Terminal Output
            </span>
          </div>
          <span className="rounded-lg bg-white/5 px-3 py-1 text-[10px] font-bold text-white/40">
            {visibleLines} events
          </span>
        </div>
        <div
          ref={logRef}
          className="custom-scrollbar flex-1 space-y-2 overflow-auto p-6 font-mono text-[11px]"
        >
          {DEMO_BOT_LOGS.slice(0, visibleLines).map((log, i) => (
            <div
              key={i}
              className={`flex items-start gap-3 rounded-lg border px-3 py-2 fadeIn ${levelColor(log.level)}`}
            >
              <span className="mt-0.5 w-16 shrink-0 tabular-nums opacity-50">
                {`14:${String(30 + Math.floor(i / 3)).padStart(2, '0')}:${String((i * 7) % 60).padStart(2, '0')}`}
              </span>
              <span className="mt-1 flex w-4 shrink-0 justify-center opacity-80">
                {eventIcon(log.event)}
              </span>
              <span className="break-all leading-relaxed">{log.message}</span>
            </div>
          ))}
          {visibleLines < DEMO_BOT_LOGS.length && (
            <div className="flex items-center gap-2 px-3 py-2">
              <div className="h-3 w-2 animate-pulse bg-amber-500" />
              <span className="text-[10px] text-white/20">Processing...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
